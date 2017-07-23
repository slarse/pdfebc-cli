# -*- coding: utf-8 -*-
"""Main module for the PDFEBC project.

Author: Simon Larsén
"""
import os
import shutil
import smtplib
import sys
from pdfebc_core import config_utils, email_utils, compress
from tqdm import tqdm
from . import cli

AUTH_ERROR = """An authentication error has occured!
Status code: {}
Message: {}

This usually happens due to incorrect username and/or password in the configuration file, 
so please look it over!"""

UNEXPECTED_ERROR = """An unexpected error occurred when attempting to send the e-mail.

Python error repr: {}

Please open an issue about this error at 'https://github.com/slarse/pdfebc/issues'.
"""

OUT_DIR_IS_FILE = """The specified output directory ({}) is a file!
Please specify a path to either an existing directory, or to where you wish to create one."""


def main():
    """Run PDFEBC."""
    try:
        parser = cli.create_argparser()
    except (config_utils.ConfigurationError, IOError):
        cli.diagnose_config()
        sys.exit(1)
    args = parser.parse_args()
    if args.configstatus:
        cli.diagnose_config()
        sys.exit(0)
    if os.path.isfile(args.outdir):
        cli.status_callback(OUT_DIR_IS_FILE.format(args.outdir))
        sys.exit(1)
    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    filepaths = compress_files(args.srcdir, args.outdir, args.ghostscript)
    if args.email:
        if not config_utils.valid_config_exists():
            # TODO Add step-by-step config creation here.
            pass
        try:
            email_utils.send_files_preconf(filepaths)
        except smtplib.SMTPAuthenticationError as e:
            cli.status_callback(AUTH_ERROR.format(e.smtp_code, e.smtp_error))
        except Exception as e:
            cli.status_callback(UNEXPECTED_ERROR.format(repr(e)))
    if args.clean:
        shutil.rmtree(args.outdir)

def compress_files(srcdir, outdir, ghostscript):
    """Compress the PDF files in srcdir and put the results in outdir.

    Args:
        srcdir (str): Source directory.
        outdir (str): Output directory.
        ghostscript (str): Name of the Ghostscript binary.

    Returns:
        List[str]: output paths.
    """
    compress_gen = compress.compress_multiple_pdfs(srcdir, outdir, ghostscript)
    amount_of_files = next(compress_gen)
    filepaths = [filepath for filepath in
                 tqdm(compress_gen, desc='Compressing {} files ...'.format(
                     amount_of_files), total=amount_of_files)]
    return filepaths


if __name__ == '__main__':
    main()
