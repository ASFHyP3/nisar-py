"""TODO"""

import logging
from argparse import ArgumentParser

from nisar_py.process import TODO


# TODO
def main() -> None:
    """TODO"""
    parser = ArgumentParser()

    # TODO: Your arguments here
    parser.add_argument('--greeting', default='Hello world!', help='Write this greeting to a product file')

    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO
    )

    product_file = TODO(
        greeting=args.greeting,
    )


if __name__ == '__main__':
    main()
