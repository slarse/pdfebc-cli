# -*- coding: utf-8 -*-
"""Main module for the PDFEBC project.

Author: Simon Larsén
"""
import os
import shutil
import smtplib
import sys
import asyncio
import itertools
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
            loop = asyncio.get_event_loop()
            loop.run_until_complete(email_supervisor(filepaths))
            print(email_utils.FILES_SENT)
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

async def working_animation(msg):
    """Print an animation to stdout.

    Args:
        msg (str): A message to come after the animation.
    """
    write, flush = sys.stdout.write, sys.stdout.flush
    erase = lambda s: write('\x08' * len(s))
    right_arrows = reversed(sorted(set(itertools.permutations('>     '))))
    left_arrows = sorted(set(itertools.permutations('<     ')))
    arrow_bars = itertools.chain(right_arrows, left_arrows)
    for arrow_bar in itertools.cycle(arrow_bars):
        status = ''.join(arrow_bar) + ' ' + msg
        write(status)
        flush()
        erase(status)
        try:
            await asyncio.sleep(.1)
        except asyncio.CancelledError:
            break
    erase(status)

async def send_files(filepaths):
    """Send the files with the settings in the config.

    Args:
        filepaths List[str]: A list of filepaths.
    """
    config = config_utils.read_config()
    args = (email_utils.get_attribute_from_config(config, email_utils.EMAIL_SECTION_KEY, attribute)
            for attribute in [email_utils.USER_KEY, email_utils.RECEIVER_KEY,
                              email_utils.SMTP_SERVER_KEY, email_utils.SMTP_PORT_KEY])
    args = itertools.chain(args, ['\n'.join(filepaths)])
#    print(email_utils.SENDING_PRECONF.format(*args))
    await email_utils.send_files_preconf(filepaths)
#    print(email_utils.FILES_SENT)

async def supervisor(work_func, animation_func):
    """Show the animation on standard out while the async function runs.

    Args:
        work_func (asyncio.coroutine): Any asynchronous function.
        animation_func (asyncio.coroutine): An asynchronous function that prints an animation
        to stdout.
    """
    animation = asyncio.ensure_future(animation_func())
    await work_func()
    animation.cancel()

async def email_supervisor(filepaths):
    animation = asyncio.ensure_future(working_animation('Sending files ...'))
    await send_files(filepaths)
    animation.cancel()

async def slow_func():
    await asyncio.sleep(3)

if __name__ == '__main__':
    main()
