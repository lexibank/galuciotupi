import re
import pathlib
import itertools
import collections
import unicodedata

from clldutils.text import strip_chars, strip_brackets

from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.forms import FormSpec

# language id fixes for raw data (as converted from pdf source)
LANGUAGE_ID_FIXES = {
    "ALL": ("Tp", "Ta"),  # set([u'Tp']) set([u'Ta'])
    "PERSON": ("Pa", "Pt"),  # set([u'Pa']) set([u'Pt'])
    "FISH": ("Pa", "Pt"),  # set([u'Pa']) set([u'Mw', u'Pt'])
    "TREE": ("Tp", "Tu"),  # set([u'Tp']) set([u'Mw', u'Tu'])
    "DRINK": ("Tp", "Ta"),  # set([u'Tp']) set([u'Kt', u'Ta'])
    "SMOKE": ("Tp", "Ta"),  # set([u'Tp']) set([u'Ta'])
    "GREEN": ("Tg", "Pg"),  # set([u'Tg']) set([u'Pg'])
    "NAME": ("Tp", "Ta"),  # set([u'Tp']) set([u'Ta'])
}


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "galuciotupi"

    form_spec = FormSpec(
        brackets={"[": "]", "(": ")"},
        separators="~",
        missing_data=(),
        strip_inside_brackets=True,
    )

    def cmd_download(self, args):
        print(
            """
Download the PDF from here:
http://www.scielo.br/pdf/bgoeldi/v10n2/2178-2547-bgoeldi-10-02-00229.pdf
and extract the text running a command like below:
pdftotext -raw galucio-tupi.pdf galucio-tupi.txt
"""
        )

    def cmd_makecldf(self, args):
        lmap = args.writer.add_languages()
        concepticon = {
            x.english: x.concepticon_id
            for x in self.conceptlists[0].concepts.values()
        }
        args.writer.add_sources(
            """
@article{Galucio2015,
    author = {Galucio, Ana Vilacy and Meira, Sérgio and Birchall, Joshua and Moore, Denny and Gabas Júnior, Nilson and Drude, Sebastian and Storto, Luciana and Picanço, Gessiane and Rodrigues, Carmen Reis},
    journal = {Boletim do Museu Paraense Emílio Goeldi. Ciências Humanas},
    pages = {229-274},
    publisher = {scielo},
    title = {Genealogical relations and lexical distances within the Tupian linguistic family},
    url = {http://www.scielo.br/scielo.php?script=sci_arttext&pid=S1981-81222015000200229&nrm=iso},
    volume = {10},
    year = {2015}
}
"""
        )

        cognate_sets = collections.defaultdict(list)
        for (cid, c), w, missing in parse(
            self.raw_dir.read("galucio-tupi.txt")
        ):
            assert c in concepticon
            if c in LANGUAGE_ID_FIXES:
                f, t = LANGUAGE_ID_FIXES[c]
                w = re.sub(f + "\s+", t + " ", w, count=1)
                missing = re.sub(f + "\s+", t + " ", missing, count=1)

            if missing:
                assert re.match(
                    "((?P<lid>%s)\s*\?\s*)+$" % "|".join(lmap), missing
                )
            missing = missing.replace("?", " ").split()

            lids = set(missing[:])
            for m in re.finditer("(?P<lid>[A-Z][a-z])\s+", w):
                lids.add(m.group("lid"))
            # make sure all language IDs are valid
            assert not lids.difference(lmap)

            nlids = missing[:]
            for cs in iter_cogsets(w, lmap):
                cognate_sets[(cid, c)].append(cs)
                nlids.extend(list(cs.keys()))
            nlids = set(nlids)
            assert nlids == lids  # make sure we found all expected language IDs

        # Add concepts
        args.writer.add_concepts(id_factory=lambda c: c.number)

        for (cid, concept), cogsets in sorted(cognate_sets.items()):
            for j, cogset in enumerate(cogsets):
                for lid, words in sorted(cogset.items(), key=lambda k: k[0]):
                    for i, word in enumerate(words):
                        for row in args.writer.add_lexemes(
                            Language_ID=lid,
                            Parameter_ID=cid,
                            Value=word,
                            Source=["Galucio2015"],
                        ):
                            args.writer.add_cognate(
                                lexeme=row, Cognateset_ID="%s-%s" % (cid, j + 1)
                            )


def parse(text):
    concept_line = re.compile("(?P<ID>[0-9]{3})-(?P<GLOSS>.+)$")
    concept, words, missing, in_appendix = None, "", "", False
    pages = text.split("\f")
    for line in itertools.chain(*[p.split("\n")[2:] for p in pages]):
        line = line.strip()
        if not line:
            continue

        # Don't start parsing before entering Appendix 1:
        if line.startswith("APPENDIX 1:"):
            in_appendix = True
            continue

        # Quit parsing once we hit Appendix 2:
        if line.startswith("APPENDIX 2:"):
            break

        if not in_appendix:
            continue

        match = concept_line.match(line)
        if match:
            if concept:
                yield concept, words, missing
            concept, words, missing = (
                (match.group("ID"), match.group("GLOSS")),
                "",
                "",
            )
        else:
            if line.startswith("("):
                assert line.endswith(")") and not missing
                missing = line[1:-1].strip()
            else:
                words += unicodedata.normalize("NFC", line.strip())

    yield concept, words, missing


def iter_lang(s, lmap):
    def pairs(l):
        for i in range(0, len(l), 2):
            yield l[i : i + 2]

    lid_pattern = re.compile(
        "(?:^|(?:,?\s+|,\s*))(?P<i>%s)\s+" % "|".join(lmap)
    )
    for language, words in pairs(lid_pattern.split(s)[1:]):
        yield language, [w.strip() for w in words.split(",") if w.strip()]


def iter_cogsets(s, lmap):
    for cogset in s.split("||"):
        cogset = cogset.strip()
        if cogset:
            yield dict(iter_lang(cogset, lmap))
