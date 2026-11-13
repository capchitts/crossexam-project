"""STEP 3d: put the papers of one shipment together. Plain code, no model.

Each paper carries identifiers: a PO number, an e-way bill number, the supplier plus the invoice number, a batch number. Those are
STRONG keys: two papers that share one belong together. A vehicle number is a WEAK key (one lorry carries many shipments), so it is
shown as a hint and never used to group. Identifiers are first normalised, so 'SI/26-27/56132' and 'si 26-27 56132' are the same.

Run:  ./run.sh ladder/step3/d_group.py
"""
from c_check import read_papers
from common import paper_files

from app.rules.normalize import norm_vehicle
from app.services.grouping import UnionFind, doc_keys


def group(papers: list[dict]) -> list[dict]:
    """Union papers that share a strong key (the same idea as group_step in the full system)."""
    uf = UnionFind()
    for i, p in enumerate(papers):
        p["strong"], p["weak"] = doc_keys(p["kind"], p["form"])
        uf.find(f"paper:{i}")
        for key in p["strong"]:
            uf.union(f"paper:{i}", f"key:{key}")
    packs: dict[str, list[dict]] = {}
    for i, p in enumerate(papers):
        packs.setdefault(uf.find(f"paper:{i}"), []).append(p)
    return list(packs.values())


def main():
    papers = [p for path in paper_files() for p in read_papers(path)]
    for n, members in enumerate(group(papers), start=1):
        po = next((m["form"].get("po_number") for m in members if m["kind"] == "invoice"), "")
        print(f"Shipment {n}: PO {po}   {len(members)} papers")
        for m in members:
            print(f"    {m['kind']:20} {m['file']:22} strong keys: {sorted(m['strong'])}")
        vehicles = {norm_vehicle(m["form"].get("vehicle_number", "")): m["form"].get("vehicle_number") for m in members if m["form"].get("vehicle_number")}
        written = sorted({m["form"].get("vehicle_number") for m in members if m["form"].get("vehicle_number")})
        print(f"    vehicle written as {written} -> one vehicle after normalising: {sorted(vehicles)}")


if __name__ == "__main__":
    main()
