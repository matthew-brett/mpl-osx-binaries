from __future__ import print_function

from subprocess import Popen, PIPE

def back_tick(cmd, ret_err=False, as_str=True, shell=False):
    """ Run command `cmd`, return stdout, or stdout, stderr if `ret_err`

    Roughly equivalent to ``check_output`` in Python 2.7

    Parameters
    ----------
    cmd : str
        command to execute
    ret_err : bool, optional
        If True, return stderr in addition to stdout.  If False, just return
        stdout
    as_str : bool, optional
        Whether to decode outputs to unicode string on exit.

    Returns
    -------
    out : str or tuple
        If `ret_err` is False, return stripped string containing stdout from
        `cmd`.  If `ret_err` is True, return tuple of (stdout, stderr) where
        ``stdout`` is the stripped stdout, and ``stderr`` is the stripped
        stderr.

    Raises
    ------
    Raises RuntimeError if command returns non-zero exit code
    """
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=shell)
    out, err = proc.communicate()
    retcode = proc.returncode
    if retcode is None:
        proc.terminate()
        raise RuntimeError(cmd + ' process did not terminate')
    if retcode != 0:
        raise RuntimeError(cmd + ' process returned code %d' % retcode)
    out = out.strip()
    if as_str:
        out = out.decode('latin-1')
    if not ret_err:
        return out
    err = err.strip()
    if as_str:
        err = err.decode('latin-1')
    return out, err
