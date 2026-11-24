# GitHub and archival-release checklist

1. Confirm the machine and complete the outstanding details in `HARDWARE.md`.
2. Confirm the author and contributor metadata in `CITATION.cff`.
3. Create an empty public GitHub repository, preferably named
   `af-fdd-all-demand-enumeration`.
4. Upload the *contents* of this directory, not the outer ZIP file as one item.
5. Add a valid `repository-code` URL to `CITATION.cff` after creating the repository.
6. Run `python verify_release.py` and `python -m pytest -q` from a fresh clone.
7. Confirm that `results/balanced/raw.csv` and
   `results/challenge/raw.csv` display or download correctly.
8. Create a GitHub release and attach the verified release archive.
9. Archive that release with Zenodo or the selected repository and obtain a DOI.
10. Add the GitHub URL and DOI to the manuscript's Data and Code Availability
    section before submission.

The raw timing files should not be edited after release. Corrections should be
documented through a new tagged version and changelog.

