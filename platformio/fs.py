# Copyright (c) 2014-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import shutil
import stat
import sys

import click

from platformio import exception
from platformio.compat import get_file_contents


class cd(object):

    def __init__(self, new_path):
        self.new_path = new_path
        self.prev_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.new_path)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.prev_path)


def get_source_dir():
    curpath = os.path.abspath(__file__)
    if not os.path.isfile(curpath):
        for p in sys.path:
            if os.path.isfile(os.path.join(p, __file__)):
                curpath = os.path.join(p, __file__)
                break
    return os.path.dirname(curpath)


def load_json(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except ValueError:
        raise exception.InvalidJSONFile(file_path)


def format_filesize(filesize):
    base = 1024
    unit = 0
    suffix = "B"
    filesize = float(filesize)
    if filesize < base:
        return "%d%s" % (filesize, suffix)
    for i, suffix in enumerate("KMGTPEZY"):
        unit = base**(i + 2)
        if filesize >= unit:
            continue
        if filesize % (base**(i + 1)):
            return "%.2f%sB" % ((base * filesize / unit), suffix)
        break
    return "%d%sB" % ((base * filesize / unit), suffix)


def ensure_udev_rules():
    from platformio.util import get_systype

    def _rules_to_set(rules_path):
        return set(l.strip() for l in get_file_contents(rules_path).split("\n")
                   if l.strip() and not l.startswith("#"))

    if "linux" not in get_systype():
        return None
    installed_rules = [
        "/etc/udev/rules.d/99-platformio-udev.rules",
        "/lib/udev/rules.d/99-platformio-udev.rules"
    ]
    if not any(os.path.isfile(p) for p in installed_rules):
        raise exception.MissedUdevRules

    origin_path = os.path.abspath(
        os.path.join(get_source_dir(), "..", "scripts",
                     "99-platformio-udev.rules"))
    if not os.path.isfile(origin_path):
        return None

    origin_rules = _rules_to_set(origin_path)
    for rules_path in installed_rules:
        if not os.path.isfile(rules_path):
            continue
        current_rules = _rules_to_set(rules_path)
        if not origin_rules <= current_rules:
            raise exception.OutdatedUdevRules(rules_path)

    return True


def rmtree(path):

    def _onerror(_, name, __):
        try:
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
        except Exception as e:  # pylint: disable=broad-except
            click.secho("%s \nPlease manually remove the file `%s`" %
                        (str(e), name),
                        fg="red",
                        err=True)

    return shutil.rmtree(path, onerror=_onerror)