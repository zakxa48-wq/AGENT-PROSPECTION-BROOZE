"""Tests du moteur : python3 -m unittest discover -s tests -v"""
import json
import os
import struct
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from moteur import experiences, importer, normalise, score, stats, temps, verif
from moteur.config import FUSEAU
from moteur.crm import CRM
from moteur.diagnostic import diagnostiquer, entonnoir, facteurs, goulot, issues_premiers_contacts
from moteur.garde_fou import Garde


def paris(*a) -> datetime:
    return datetime(*a, tzinfo=FUSEAU)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dossier = Path(self.tmp.name)
        self.crm = CRM(self.dossier)

    def tearDown(self):
        self.tmp.cleanup()

    def prospect(self, nom="Atelier Test", email="lea@atelier-test.fr", score_=80, **extra):
        d = {"nom": nom, "email": email, "email_source": "https://atelier-test.fr/contact", "score": score_,
             "verif": {"type": "nominative", "bloquant": False, "gratuit": False}, "ville": "Strasbourg"}
        d.update(extra)
        pid, _ = self.crm.ajouter_prospect(d)
        return pid

    def pret(self, pid, etape=1, note=9, quand=None):
        ts = temps.iso(quand) if quand else None
        self.crm.evenement("redige", pid, ts=ts, etape=etape, approche="A")
        self.crm.evenement("controle", pid, ts=ts, etape=etape, note=note)


class TestTemps(unittest.TestCase):
    def test_paques_et_feries_alsace(self):
        self.assertEqual(temps.paques(2027).isoformat(), "2027-03-28")
        f = temps.jours_feries(2026)
        self.assertIn(datetime(2026, 4, 3).date(), f)   # Vendredi saint (Alsace)
        self.assertIn(datetime(2026, 12, 26).date(), f)  # Saint-Étienne (Alsace)
        self.assertIn(datetime(2026, 11, 11).date(), f)

    def test_jours_ouvres(self):
        # mardi 10/11/2026 + 3 ouvrés = lundi 16/11 (le 11/11 est férié)
        self.assertEqual(temps.ajouter_jours_ouvres(datetime(2026, 11, 10).date(), 3).isoformat(), "2026-11-16")


class TestNormaliseVerif(unittest.TestCase):
    def test_normalisation(self):
        self.assertEqual(normalise.email(" <Lea@Atelier.FR>. "), "lea@atelier.fr")
        self.assertEqual(normalise.domaine("https://www.atelier.fr/contact"), "atelier.fr")
        self.assertEqual(normalise.zone("Schiltigheim", "67300"), "strasbourg")
        self.assertEqual(normalise.zone("Colmar", "68000"), "alsace")
        self.assertGreater(normalise.similarite("Le Bisch'trot", "Bischtrot"), 0.85)

    def test_types_de_boite(self):
        self.assertEqual(verif.type_boite("sav@marque.fr"), "guichet")
        self.assertEqual(verif.type_boite("contact@resto.fr"), "generique")
        self.assertEqual(verif.type_boite("contact.resto@gmail.com"), "perso")
        self.assertEqual(verif.type_boite("clemence@marque.fr"), "nominative")

    def test_verification_bloquante(self):
        self.assertTrue(verif.verifier("patron@gmial.com", "x", mx=False)["bloquant"])
        self.assertTrue(verif.verifier("pas-une-adresse", "x", mx=False)["bloquant"])
        self.assertTrue(verif.verifier("support@grande-marque.com", "x", mx=False)["bloquant"])
        ok = verif.verifier("lea@atelier.fr", "https://atelier.fr", mx=False)
        self.assertFalse(ok["bloquant"])

    def test_dns_requete_et_reponse(self):
        q = verif.construire_requete("exemple.fr", ident=0x1234)
        self.assertEqual(q[:2], b"\x12\x34")
        # Réponse synthétique : 1 question, 1 réponse MX (préférence 10, mx.exemple.fr) avec compression.
        entete = struct.pack(">HHHHHH", 0x1234, 0x8180, 1, 1, 0, 0)
        question = q[12:]
        nom_mx = b"\x02mx\xc0\x0c"
        rdata = struct.pack(">H", 10) + nom_mx
        reponse = b"\xc0\x0c" + struct.pack(">HHIH", 15, 1, 300, len(rdata)) + rdata
        rcode, mx = verif.analyser_reponse(entete + question + reponse)
        self.assertEqual(rcode, 0)
        self.assertEqual(mx, [(10, "mx.exemple.fr")])


class TestDNSFiltre(unittest.TestCase):
    def test_resolveur_filtre_donne_non_verifiable(self):
        ancien = verif._FIABLE
        try:
            verif._FIABLE = False
            self.assertIsNone(verif.verifier_mx("exemple.fr"))
            self.assertIn("MX non vérifiable", " ".join(verif.verifier("a@exemple.fr", "x")["avertissements"]))
        finally:
            verif._FIABLE = ancien


class TestImport(Base):
    def test_import_csv_mapping_doublons(self):
        chemin = self.dossier / "liste.csv"
        chemin.write_text("Entreprise;Ville;CP;E-mail;Site web;Secteur\n"
                          "Atelier Un;Strasbourg;67000;lea@atelier-un.fr;atelier-un.fr;céramique\n"
                          "Atelier Un bis;Strasbourg;67000;lea@atelier-un.fr;;céramique\n"
                          "Guichet SA;Paris;75001;sav@guichet.fr;guichet.fr;industrie\n", encoding="utf-8")
        r = importer.importer(self.crm, chemin, "test", liste_zak=True, mx=False)
        self.assertEqual(r["colonnes"]["E-mail"], "email")
        self.assertEqual(len(r["doublons_fichier"]), 1)
        self.assertEqual(len(r["adresses_bloquees"]), 1)
        p = self.crm.prospects["p-atelier-un-fr"]
        self.assertEqual(p["segment"], "B")
        self.assertEqual(p["signaux"]["zone"], "strasbourg")
        self.assertEqual(self.crm.etat("p-atelier-un-fr"), "a_qualifier")
        # Second import : reconnu comme déjà connu
        r2 = importer.importer(self.crm, chemin, "test", mx=False)
        self.assertEqual(len(r2["importes"]), 0)

    def test_xlsx_minimal(self):
        import zipfile
        chemin = self.dossier / "l.xlsx"
        with zipfile.ZipFile(chemin, "w") as z:
            z.writestr("xl/sharedStrings.xml", '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                       '<si><t>Nom</t></si><si><t>Email</t></si><si><t>Studio X</t></si><si><t>a@studiox.fr</t></si></sst>')
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                       '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'
                       '<row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row></sheetData></worksheet>')
        self.assertEqual(importer._lire_xlsx_minimal(chemin), [["Nom", "Email"], ["Studio X", "a@studiox.fr"]])


class TestGardeFou(Base):
    MARDI_10H = paris(2026, 11, 10, 10, 0)

    def test_autorise_quand_tout_est_bon(self):
        pid = self.prospect()
        self.pret(pid, quand=self.MARDI_10H - timedelta(hours=1))
        v = Garde(self.crm, self.MARDI_10H).verifier("premier_contact", pid)
        self.assertTrue(v.ok, v.raisons)

    def test_refus_week_end_ferie_et_hors_fenetre(self):
        pid = self.prospect()
        self.pret(pid)
        for t in (paris(2026, 11, 8, 10, 0), paris(2026, 11, 11, 10, 0), paris(2026, 11, 10, 12, 30)):
            self.assertFalse(Garde(self.crm, t).verifier("premier_contact", pid).ok)

    def test_plafond_et_espacement(self):
        g_t = self.MARDI_10H
        for i in range(10):
            pid = self.prospect(nom=f"Studio {i}", email=f"a@studio{i}.fr")
            self.pret(pid, quand=g_t - timedelta(days=1))
            Garde(self.crm, g_t - timedelta(minutes=60 - i * 4)).enregistrer_envoi(pid, "premier_contact", 1, "A")
        pid = self.prospect(nom="Studio 11", email="a@studio11.fr")
        self.pret(pid, quand=g_t - timedelta(days=1))
        v = Garde(self.crm, g_t + timedelta(minutes=30)).verifier("premier_contact", pid)
        self.assertFalse(v.ok)
        self.assertTrue(any("plafond" in r for r in v.raisons))
        # Une réponse à un prospect qui nous écrit reste possible
        self.crm.evenement("reponse", pid, classe="positive")
        self.assertTrue(Garde(self.crm, g_t + timedelta(minutes=30)).verifier("reponse", pid).ok)

    def test_espacement_minimal(self):
        a, b = self.prospect(nom="A", email="a@a-test.fr"), self.prospect(nom="B", email="b@b-test.fr")
        self.pret(a, quand=self.MARDI_10H - timedelta(days=1))
        self.pret(b, quand=self.MARDI_10H - timedelta(days=1))
        Garde(self.crm, self.MARDI_10H).enregistrer_envoi(a, "premier_contact", 1, "A")
        v = Garde(self.crm, self.MARDI_10H + timedelta(minutes=1)).verifier("premier_contact", b)
        self.assertTrue(any("minimum 3 min" in r for r in v.raisons))

    def test_pause_limite_et_bounces(self):
        pid = self.prospect()
        self.pret(pid)
        self.crm.evenement("limite_envoi", None, ts=temps.iso(self.MARDI_10H - timedelta(hours=2)))
        self.assertFalse(Garde(self.crm, self.MARDI_10H).verifier("reponse", pid).ok)
        (self.dossier / "PAUSE").write_text("stop")
        self.assertIn("PAUSE", Garde(self.crm, self.MARDI_10H + timedelta(days=3)).verifier("relance", pid).raisons[0])

    def test_sans_sceptique_ou_note_basse(self):
        pid = self.prospect()
        self.crm.evenement("redige", pid, etape=1)
        self.assertTrue(any("Sceptique" in r for r in Garde(self.crm, self.MARDI_10H).verifier("premier_contact", pid).raisons))
        self.crm.evenement("controle", pid, etape=1, note=7)
        self.assertTrue(any("note du Sceptique" in r for r in Garde(self.crm, self.MARDI_10H).verifier("premier_contact", pid).raisons))

    def test_doublon_de_structure_et_relance(self):
        a = self.prospect(nom="Maison Un", email="lea@maison-un.fr")
        self.pret(a, quand=self.MARDI_10H - timedelta(days=1))
        Garde(self.crm, self.MARDI_10H).enregistrer_envoi(a, "premier_contact", 1, "A")
        b, cree = self.crm.ajouter_prospect({"nom": "Autre", "email": "paul@maison-un.fr"}, autoriser_doublon=True)
        self.crm.prospects[b].update(email_source="x", score=90, verif={"type": "nominative"})
        self.pret(b)
        v = Garde(self.crm, self.MARDI_10H + timedelta(hours=1)).verifier("premier_contact", b)
        self.assertTrue(any("déjà contactée" in r for r in v.raisons))
        # Relance 2 : pas avant J+3 ouvrés (vendredi 13/11 car le 11 est férié)
        self.pret(a, etape=2)
        self.assertFalse(Garde(self.crm, paris(2026, 11, 12, 10, 0)).verifier("relance", a, 2).ok)
        self.assertTrue(Garde(self.crm, paris(2026, 11, 16, 10, 0)).verifier("relance", a, 2).ok)

    def test_historique_ne_bloque_pas_la_sante(self):
        for i in range(30):
            pid = self.prospect(nom=f"H{i}", email=f"x@h{i}.fr")
            self.crm.evenement("envoye", pid, ts="2026-10-01T08:00:00+00:00", historique=True, etape=1)
            if i % 3 == 0:
                self.crm.evenement("rebond", pid, ts="2026-10-01T08:05:00+00:00", historique=True)
        pid = self.prospect(nom="Neuf", email="a@neuf-test.fr")
        self.pret(pid)
        self.assertTrue(Garde(self.crm, self.MARDI_10H).verifier("premier_contact", pid).ok)


class TestStatsExperiences(Base):
    def test_stats(self):
        self.assertGreater(stats.proba_superieur(20, 100, 5, 100), 0.99)
        self.assertAlmostEqual(stats.proba_superieur(5, 50, 5, 50), 0.5, delta=0.05)
        self.assertEqual(stats.niveau_preuve(0.99, True, tests=1), "prouvé")
        self.assertEqual(stats.niveau_preuve(0.96, True, tests=10), "probable")  # corrigé du nombre de tests

    def test_maturation(self):
        conf = json.loads((Path(__file__).parent.parent / "config" / "approches.json").read_text())
        self.assertEqual(experiences.maturation(0, conf), 0.0)
        self.assertEqual(experiences.maturation(30, conf), 1.0)
        self.assertGreater(experiences.maturation(3, conf), 0.45)

    def _envois(self, bras, n, positifs, quand):
        for i in range(n):
            pid = self.prospect(nom=f"{bras}{i}", email=f"a@{bras.lower()}{i}-x.fr")
            self.crm.evenement("envoye", pid, ts=temps.iso(quand), etape=1, type_envoi="premier_contact",
                               dims={"approche": bras})
            if i < positifs:
                self.crm.evenement("reponse", pid, ts=temps.iso(quand + timedelta(days=1)), classe="positive")

    def test_thompson_renforce_le_meilleur_et_garde_le_temoin(self):
        t0 = paris(2026, 10, 1, 10)
        self._envois("A", 60, 2, t0)
        self._envois("B", 60, 12, t0)
        self._envois("C", 60, 1, t0)
        alloc = experiences.allouer(10, self.crm, maintenant=paris(2026, 11, 10, 9))
        self.assertGreaterEqual(alloc.count("A"), 3)   # part minimale du témoin
        self.assertGreaterEqual(alloc.count("C"), 1)   # part minimale de chaque bras
        self.assertGreaterEqual(alloc.count("B"), 5)   # le meilleur est renforcé
        dec = {d["bras"]: d for d in experiences.decisions(self.crm, maintenant=paris(2026, 11, 10, 9))}
        self.assertIn("champion", dec["B"]["avis"])


class TestDiagnostic(Base):
    def _cohorte(self, nb, reponses, zone, adresse, historique=True):
        for i in range(nb):
            pid = self.prospect(nom=f"{zone}{adresse}{i}", email=f"z@{zone}{adresse}{i}.fr", signaux={"zone": zone},
                                verif={"type": adresse})
            self.crm.evenement("envoye", pid, ts="2026-10-01T08:00:00+00:00", historique=historique, etape=1)
            if i < reponses:
                self.crm.evenement("reponse", pid, ts="2026-10-02T08:00:00+00:00", historique=historique,
                                   classe="positive" if i % 2 == 0 else "deja_videaste")

    def test_facteur_zone_prouve(self):
        self._cohorte(60, 15, "strasbourg", "perso")
        self._cohorte(60, 0, "france", "generique")
        lignes = issues_premiers_contacts(self.crm)
        f = {x["dimension"]: x for x in facteurs(lignes, "reponse")}
        self.assertEqual(f["zone"]["meilleur"]["valeur"], "strasbourg")
        self.assertEqual(f["zone"]["niveau"], "prouvé")

    def test_goulot_et_causes(self):
        self._cohorte(60, 15, "strasbourg", "perso")
        self._cohorte(60, 0, "france", "generique")
        d = diagnostiquer(self.crm)
        self.assertIsNotNone(d["goulot"])
        ids = {c["id"]: c for c in d["causes"]}
        self.assertEqual(ids["C2"]["niveau"], "prouvé")
        self.assertIn(ids["O2"]["niveau"], ("prouvé", "probable"))  # « déjà un vidéaste » domine

    def test_entonnoir_insuffisant(self):
        e = entonnoir([], {"delivrabilite": 0.98})
        self.assertEqual(e[0]["statut"], "données insuffisantes")
        self.assertIsNone(goulot(e))


class TestHistorique(Base):
    def test_import_historique_et_reponses_passees(self):
        h = [{"email": "a@resto-un.fr", "nom": "Resto Un", "date_premier": "2026-09-20T08:00:00+00:00",
              "envois": ["2026-09-20T08:00:00+00:00"], "issue": "reponse", "classe": "positive",
              "date_reponse": "2026-09-21T08:00:00+00:00", "zone": "strasbourg", "segment": "A",
              "dims": {"campagne": "locale", "rafale_10min": "1-2"}},
             {"email": "b@bloque.fr", "date_premier": "2026-09-20T08:01:00+00:00", "issue": "rebond",
              "nature_echec": "bloque", "date_reponse": "2026-09-20T08:01:05+00:00", "dims": {"rafale_10min": "6+"}}]
        chemin = self.dossier / "h.json"
        chemin.write_text(json.dumps(h), encoding="utf-8")
        bilan = importer.importer_historique(self.crm, chemin)
        self.assertEqual(bilan["crees"], 2)
        # une réponse historique n'est pas une urgence du jour…
        self.assertEqual(self.crm.reponses_sans_suite(), [])
        # … et l'historique ne compte ni dans les plafonds ni dans la santé du jour
        g = Garde(self.crm, paris(2026, 11, 10, 10))
        self.assertEqual(g.premiers_contacts_du_jour(), 0)
        self.assertEqual(g.taux_rebond_50(), (0.0, 0))
        lignes = issues_premiers_contacts(self.crm)
        self.assertEqual(sum(l["rebond"] for l in lignes), 1)
        self.assertEqual(lignes[0]["dims"]["campagne"], "locale")


class TestScore(Base):
    def test_score_et_exclusion(self):
        p = {"ville": "Strasbourg", "code_postal": "67000", "verif": {"type": "nominative"},
             "signaux": {"declencheur": "ouverture", "actif_14j": True}}
        s = score.calculer(p)
        self.assertEqual(s["score"], 20 + 15 + 20 + 10)
        self.assertEqual(score.calculer({**p, "verif": {"type": "guichet"}})["score"], 0)


if __name__ == "__main__":
    unittest.main()
