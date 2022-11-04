#!/usr/bin/env python3

import argparse
from pathlib import Path

from aarch64_experimental_disasm.cpp_gen import gen_cpp
from aarch64_experimental_disasm.mra_encoding_xml import *
from rich import print


def print_encoding(enc: Encoding):
    pm = enc.pos_mask
    pv = enc.pos_val
    nm = enc.neg_mask
    nv = enc.neg_val
    pmbs = f"{pm:#034b}"[2:]
    pvbs = f"{pv:#034b}"[2:]
    nmbs = f"{nm:#034b}"[2:]
    nvbs = f"{nv:#034b}"[2:]
    bs = ["-"] * 32
    for i in range(32):
        assert not (nmbs[i] == "1" and pmbs[i] == "1")
        if nmbs[i] == "1":
            if nvbs[i] == "0":
                bs[i] = "*"
            else:
                bs[i] = "|"
        elif pmbs[i] == "1":
            if pvbs[i] == "0":
                bs[i] = "0"
            else:
                bs[i] = "1"
    bs = "".join(bs)
    print(f"{bs};{enc.mnemonic};{enc.name}")


def dupes(items) -> list:
    seen = set()
    res = []
    for x in items:
        if x in seen:
            res.append(x)
        else:
            seen.add(x)
    return res


def dup_check(encs: list[Encoding]) -> None:
    print(len(encs))
    enc_tup = [(e.pos_mask, e.pos_val, e.neg_mask, e.neg_val) for e in encs]
    dups = dupes(enc_tup)
    print(len(enc_tup))
    print(len(dups))
    print(dups)


def real_main(args):
    if args.xml_dir is not None:
        encs = parse_encodings_xml(args.xml_dir)
    elif args.xml_inst is not None:
        encs = parse_instruction_xml(args.xml_inst)
    else:
        raise ValueError("Must provide XML dir or instruction file")
    if args.dump_enc:
        for enc in encs:
            print_encoding(enc)
    if args.dup_check:
        dup_check(encs)
    if args.cpp_gen is not None:
        gen_cpp(args.cpp_gen, encs)


def get_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="aarch64-dump-instrs")
    parser.add_argument("-x", "--xml-dir", type=Path, help="MRA XML directory")
    parser.add_argument("-i", "--xml-inst", type=Path, help="MRA XML instruction file")
    parser.add_argument("-d", "--dump-enc", action="store_true", help="dump encodings textually")
    parser.add_argument("-c", "--cpp-gen", type=Path, help="write C++ decoder")
    parser.add_argument(
        "-D", "--dup-check", action="store_true", help="check for duplicate encodings"
    )
    return parser


def main():
    real_main(get_arg_parser().parse_args())


if __name__ == "__main__":
    main()
