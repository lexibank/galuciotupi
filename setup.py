from setuptools import setup
import sys
import json


with open("metadata.json", encoding="utf-8") as fp:
    metadata = json.load(fp)


setup(
    name="lexibank_galuciotupi",
    description=metadata["title"],
    license=metadata.get("license", ""),
    url=metadata.get("url", ""),
    py_modules=["lexibank_galuciotupi"],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "lexibank.dataset": ["galuciotupi=lexibank_galuciotupi:Dataset"]
    },
    extras_require={"test": ["pytest-cldf"]},
    install_requires=["pylexibank>=2.1"],
)
