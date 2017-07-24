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

CLEANING = "Cleaning up ..."

def main():
    """Run PDFEBC."""
    try:
        parser = cli.create_argparser()
    except (config_utils.ConfigurationError, IOError):
        cli.diagnose_config()
        sys.exit(1)
    args = parser.parse_args()
    if args.configstatus:
        diagnose_config_and_exit()
    exit_if_path_is_file(args.outdir)
    makedirs_if_path_does_not_exist(args.outdir)
    filepaths = compress_files(args.srcdir, args.outdir, args.ghostscript)
    if args.email:
        handle_email(filepaths)
    if args.clean:
        clean_output(args.outdir)

def diagnose_config_and_exit():
    """Diagnose the config if the corresponding cli option is set, and then exit."""
    cli.diagnose_config()
    sys.exit(0)

def exit_if_path_is_file(outdir):
    """Check if the output directory is a file. If it is, exit the program and
    print an error message.

    Args:
        outdir (str): Path to the output directory.
    """
    if os.path.isfile(outdir):
        cli.status_callback(OUT_DIR_IS_FILE.format(outdir))
        sys.exit(1)

def makedirs_if_path_does_not_exist(path):
    """Create the directory and any missing intermediate directories,
    if the path does not exist.

    Args:
        path (str): Path to a directory.
    """
    if not os.path.isdir(path):
        os.makedirs(path)

def handle_email(filepaths):
    """Handle everything related to the email argument.

    Args:
        email (bool): A boolean value.
        filepaths (List[str]): A list of filepaths.
    """
    if not config_utils.valid_config_exists():
        # TODO Add step-by-step config creation here.
        pass
    try:
        cli.status_callback(send_files_status_message(filepaths))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(email_supervisor(filepaths))
    except smtplib.SMTPAuthenticationError as e:
        cli.status_callback(AUTH_ERROR.format(e.smtp_code, e.smtp_error))
    except Exception as e:
        cli.status_callback(UNEXPECTED_ERROR.format(repr(e)))
    
def clean_output(outdir):
    """Print a status message and remove the output directory."""
    cli.status_callback(CLEANING)
    shutil.rmtree(outdir)

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
    """cli.status_callback an animation to stdout.

    Args:
        msg (str): A message to come after the animation.
    """
    write, flush = sys.stdout.write, sys.stdout.flush
    erase = lambda s: write('\x08'*len(s))
    right_arrows = reversed(sorted(set(itertools.permutations('>' + ' '*4))))
    left_arrows = sorted(set(itertools.permutations('<' + ' '*4)))
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

def send_files_status_message(filepaths):
    """Returns:
        str: The send file status message.
    """
    config = config_utils.read_config()
    args = (email_utils.get_attribute_from_config(config, email_utils.EMAIL_SECTION_KEY, attribute)
            for attribute in [email_utils.USER_KEY, email_utils.RECEIVER_KEY,
                              email_utils.SMTP_SERVER_KEY, email_utils.SMTP_PORT_KEY])
    args = itertools.chain(args, ['\n'.join(filepaths)])
    return email_utils.SENDING_PRECONF.format(*args)

async def send_files(filepaths):
    """Send the files with the settings in the config.

    Args:
        filepaths List[str]: A list of filepaths.
    """
    await email_utils.send_files_preconf(filepaths)
    cli.status_callback(email_utils.FILES_SENT)

async def supervisor(work_func, animation_func):
    """Show the animation on standard out while the async function runs.

    Args:
        work_func (asyncio.coroutine): Any asynchronous function.
        animation_func (asyncio.coroutine): An asynchronous function that cli.status_callbacks an animation
        to stdout.
    """
    animation = asyncio.ensure_future(animation_func())
    await work_func()
    animation.cancel()

async def email_supervisor(filepaths):
    animation = asyncio.ensure_future(working_animation('Sending files ...'))
    await send_files(filepaths)
    animation.cancel()

if __name__ == '__main__':
    main()
