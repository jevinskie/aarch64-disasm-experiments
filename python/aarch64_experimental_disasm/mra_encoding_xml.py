import re
from pathlib import Path
from typing import Optional, Union

import lxml.objectify
from attrs import define
from lxml import objectify
from rich import print


@define
class Constraint:
    pos: int
    sz: int
    val: int
    neg: bool


@define
class Field:
    pos: int
    sz: int
    constraints: Optional[tuple[Constraint]]
    name: Optional[str]


@define
class Encoding:
    mnemonic: str
    name: str
    path: Path
    pos_mask: int
    pos_val: int
    neg_mask: int
    neg_val: int
    fields: tuple[Field]


def bitmask(pos: int, nbits: int) -> int:
    hi_mask = (1 << (pos + nbits)) - 1
    lo_mask = (1 << pos) - 1
    return hi_mask ^ lo_mask


# FIXME
def pack_constraints(constraints: list[Constraint]) -> list[Constraint]:
    packed = []
    csz = len(constraints)
    if csz < 2:
        return constraints
    prev_c = constraints[0]
    new_c = None
    for i in range(1, csz):
        this_c = constraints[i]
        if prev_c.pos - prev_c.sz == this_c.pos and prev_c.neg == this_c.neg:
            new_c = Constraint()
        else:
            packed.append(prev_c)
        prev_c = this_c
    if csz == 6:
        pass
    return packed


def parse_box(box) -> Field:
    sz = 1 if "width" not in box.attrib else int(box.attrib["width"])
    pos = int(box.attrib["hibit"]) - (sz - 1)
    name = None
    if "name" in box.attrib and "usename" in box.attrib:
        name = box.attrib["name"]
    if all(c.text is None for c in box.c):
        constraints = None
    else:
        if "constraint" in box.attrib:
            cstr = box.attrib["constraint"]
            if not cstr.startswith("!= "):
                constraints = [Constraint(0, len(cstr), int(cstr, 2), False)]
            else:
                cstr = cstr.removeprefix("!= ")
                constraints = [Constraint(0, len(cstr), int(cstr, 2), True)]
        else:
            constraints = []
            csz = len(box.c)
            for i, c in enumerate(box.c):
                if c.text == "0" or c.text == "(0)":
                    constraints.append(Constraint(csz - i - 1, 1, 0, False))
                elif c.text == "1" or c.text == "(1)":
                    constraints.append(Constraint(csz - i - 1, 1, 1, False))
                elif c.text == "x" or c.text == "(x)":
                    pass
                else:
                    raise ValueError(f"got weird bit '{c.text}'")
    return Field(pos, sz, constraints, name)


def parse_boxes(boxes: lxml.objectify.ObjectifiedElement) -> tuple[Field]:
    fields = []
    for b in boxes:
        fields.append(parse_box(b))
    return tuple(fields)


def parse_fields(fields: tuple[Field]) -> tuple[int, int, int, int]:
    pos_mask, pos_val, neg_mask, neg_val = 0, 0, 0, 0
    for f in fields:
        if f.constraints is None:
            continue
        c = f.constraints
        for sub_c in c:
            if not sub_c.neg:
                pos_mask |= bitmask(f.pos + sub_c.pos, sub_c.sz)
                pos_val |= sub_c.val << (f.pos + sub_c.pos)
            else:
                neg_mask |= bitmask(f.pos + sub_c.pos, sub_c.sz)
                neg_val |= sub_c.val << (f.pos + sub_c.pos)
    return pos_mask, pos_val, neg_mask, neg_val


def parse_instruction_xml(xml_instsect_file: Path) -> list[Encoding]:
    encodings = []
    tree = objectify.parse(str(xml_instsect_file))
    if tree.docinfo.internalDTD.name != "instructionsection":
        return []
    iclasses = tree.getroot().classes.iclass
    for iclass in iclasses:
        path = iclass.regdiagram.attrib["psname"]
        path = path.replace("aarch64/instrs", "aarch64")
        path = Path(path).parent
        name = iclass.encoding.attrib["name"]
        mnemonic = next(
            filter(lambda dv: dv.attrib["key"] == "mnemonic", iclass.encoding.docvars.docvar)
        ).attrib["value"]
        fields = parse_boxes(iclass.regdiagram.box)
        pos_mask, pos_val, neg_mask, neg_val = parse_fields(fields)
        enc = Encoding(mnemonic, name, path, pos_mask, pos_val, neg_mask, neg_val, fields)
        encodings.append(enc)
    return encodings


def parse_encodings_xml(xml_dir: Path) -> list[Encoding]:
    encodings = []
    xml_files = xml_dir.glob("*.xml")
    for f in xml_files:
        encodings.append(parse_instruction_xml(f))
    return encodings
