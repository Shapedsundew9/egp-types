"""Command line tool to generate hashes for GC interface definitions.


USAGE: interface_hashes [--help] FILE

Generates the ordered and unordered hashes for the given GC interface definition. The interface definition
must be a JSON file with the following structure:
    [[ep_type, ep_type, ...], [ep_type, ep_type, ...]]
where ep_type is an endpoint type string and the first list the GC input interface, the second the GC output.
An empty list is allowed for the input or output interface.
Examples:
    [[], ["int", "float", "str"]]
    [["int", "float", "str"], []]
    [["int", "float", "str"], ["int", "float", "str"]]
FILE must be a path to a JSON file with the above structure or '-' to read from stdin.   
"""

from argparse import ArgumentParser, Namespace
from json import loads, load
from egp_types.ep_type import interface_definition, ordered_interface_hash, unordered_interface_hash, vtype


if __name__ == '__main__':
    parser = ArgumentParser(
        description="""Generate the ordered and unordered interface hashes. The interface definition
                    must be a JSON file with the following structure:\n
                    \t[[ep_type, ep_type, ...], [ep_type, ep_type, ...]]\n
                    where ep_type is an endpoint type string and the first list the GC input interface, the second the GC output.
                    An empty list is allowed for the input or output interface.\nExamples:\n
                    \t[[], ["int", "float", "str"]],\n\t[["int", "float", "str"], []],\n\t[["int", "float", "str"], ["int", "float", "str"]]
        """)
    parser.add_argument('file', metavar='FILE', help='JSON file with the interface definition or "-" to read from stdin')
    args: Namespace = parser.parse_args()
    if args.file == '-':
        try:
            interface: list[list[str]] = loads(input())
        except ValueError:
            print('Invalid JSON.')
            exit(1)
    else:
        with open(args.file, 'r', encoding="utf-8") as f:
            try:
                interface = load(f)
            except ValueError:
                print('Invalid JSON.')
                exit(1)

    in_eps, _, ins = interface_definition(interface[0], vtype.EP_TYPE_STR)
    out_eps, _, outs = interface_definition(interface[1], vtype.EP_TYPE_STR)

    print('Ordered hash:   {}'.format(ordered_interface_hash(in_eps, out_eps, ins, outs)))
    print('Unordered hash: {}'.format(unordered_interface_hash(in_eps, out_eps)))


