#!/usr/bin/env python3
# Brian Koopman

import os
import time

from progress.bar import Bar

from so3g import hk
from ocs.ocs_feed import Feed

from colorama import init, Fore, Style
init()


def _build_file_list(target):
    """Build list of files to scan.

    Parameters
    ----------
    target : str
        File or directory to scan.

    Returns
    -------
    list
        List of full paths to files for scanning.

    """
    _file_list = []
    if os.path.isfile(target):
        _file_list.append(target)
    elif os.path.isdir(target):
        a = os.walk(target)
        for root, _, _file in a:
            for g3 in _file:
                if g3[-2:] == "g3":
                    _file_list.append(os.path.join(root, g3))

    return _file_list


class DataChecker:
    """Check data for latest feeds and fields.

    Parameters
    ----------
    target : str
        File or directory to scan.
    verbose : bool
        Verbose output flag

    Attributes
    ----------
    hkas : so3g.hk.HKArchiveScanner
        HKArchiveScanner for reading in the data
    cat :
        Finalized HKArchiveScanner
    target : str
        File or directory to scan.
    verbose : bool
        Verbose output flag
    fields : dict
        fields returned from a cat.get_fields call
    timelines : dict
        timelines returned from a cat.get_fields call
    instances : dict
        Agent/feed/field information for each instance-id, format described in
        _populate_instances docstring

    """

    def __init__(self, target, verbose=False):
        self.target = target
        self.verbose = verbose

        self.hkas = hk.HKArchiveScanner()
        self.cat = None

        self.fields = None
        self.timelines = None

        self.instances = {}

        # Private attributes
        self._file_list = _build_file_list(target)
        self._field_count = 0

    def scan_files(self):
        """Scan all the files with the HKArchiveScanner for later processing."""
        _bar = Bar('Scanning', max=len(self._file_list))
        for _file in self._file_list:
            try:
                self.hkas.process_file(_file)
            except Exception as e:
                print(e)
            _bar.next()
        _bar.finish()

        self.cat = self.hkas.finalize()

    def _populate_instances(self):
        """Populate the instances dictionary with information about each agent,
        the agent's feeds, and the associated fields.

        For each instance ID there is a dictionary like:
        {INSTANCE_ID:
            {FEED1:
                {"fields":
                   {FIELD1:
                       {'full_name': 'ADDRESS_ROOT.INSTANCE_ID.feeds.FEED.FIELD',
                        't_last': float,
                        'v_last': float},
                    FIELD2:
                       {'full_name': 'ADDRESS_ROOT.INSTANCE_ID.feeds.FEED.FIELD',
                        't_last': float,
                        'v_last': float}
                    },
                 "t_last" : lowest t_last in all fields
                }
             FEED2: {},
             FEED3: {},
             ...
            }
        }

        """

        for field_name in sorted(self.fields):
            site, instance_id, _, feed, field = field_name.split(".")

            if instance_id not in self.instances:
                self.instances[instance_id] = {}

            if feed not in self.instances[instance_id]:
                self.instances[instance_id][feed] = {"fields": {},
                                                     "t_last": None}

            if field not in self.instances[instance_id][feed]:
                self.instances[instance_id][feed]["fields"][field] = \
                    {'full_name': field_name,
                     't_last': None,
                     'v_last': None}
                self._field_count += 1

    def process_files(self):
        """Process all files, resquesting simple data points for each dataset
        and determining the last time we saw the field and the last value that
        field held.

        """
        _bar = Bar('Processing', max=self._field_count)
        for instance_id, feeds in self.instances.items():
            for feed, fields in feeds.items():
                for field, d_info in fields['fields'].items():
                    t, x = self.cat.simple(d_info['full_name'])
                    d_info['t_last'] = t[-1]
                    d_info['v_last'] = x[-1]

                    if fields['t_last'] is None:
                        fields['t_last'] = t[-1]
                    elif t[-1] < fields['t_last']:
                        fields['t_last'] = t[-1]
                    else:
                        pass

                    _bar.next()
        _bar.finish()
        print()

    def run(self):
        """Run data checker, scan and process all files in target."""
        self.scan_files()
        self.fields, self.timelines = self.cat.get_fields()
        self._populate_instances()
        self.process_files()

    def __str__(self):
        """Print informative string representing the data checker results."""
        description_string = ""

        for instance_id, feeds in self.instances.items():
            description_string += f"{instance_id}\n"
            for feed, fields in feeds.items():
                if not self.verbose:
                    field_t_diff = time.time() - fields['t_last']
                    if field_t_diff > 600:
                        description_string += f"  {feed}: " + Fore.RED + f"{field_t_diff:.1f} s old\n" + Style.RESET_ALL
                    else:
                        description_string += f"  {feed}: {field_t_diff:.1f} s old\n"
                else:
                    # Determine width of "Field" column
                    field_str_len = 20
                    for _f in fields['fields']:
                        if len(_f) > field_str_len:
                            field_str_len = len(_f)

                    description_string += f"  {feed}\n"
                    # 20 per fixed field, 9 for dividers, and field_str_len
                    description_string += "  " + "-" * (69 + field_str_len) + "\n"

                    # Header string
                    desc_substring = "  "

                    # Field
                    _field_string = "Field".rjust(field_str_len)
                    desc_substring += _field_string + " | "

                    # Last Seen [s ago]
                    _t_diff_string = "{:>20}".format("Last Seen [s ago]")
                    desc_substring += _t_diff_string + " | "

                    # Seen At [ctime]
                    _t_last_string = "{:>20}".format("Seen At [ctime]")
                    desc_substring += _t_last_string + " | "

                    # Value
                    _v_last_string = "{:>20}".format("Value")
                    desc_substring += _v_last_string

                    description_string += desc_substring + "\n"

                    description_string += "  " + "-" * (69 + field_str_len) + "\n"

                    for field, d_info in fields['fields'].items():
                        t_diff = time.time() - d_info['t_last']
                        desc_substring = "  "

                        # Field
                        try:
                            valid_field = Feed.verify_data_field_string(field)
                        except ValueError:
                            valid_field = False
                        _field_string = field.rjust(field_str_len)
                        if not valid_field:
                            _field_string = Fore.YELLOW + _field_string + Style.RESET_ALL
                        desc_substring += _field_string + " | "

                        # Last Seen [s ago]
                        _t_diff_string = "{:>20.1f}".format(t_diff)
                        if t_diff > 600:
                            _t_diff_string = Fore.RED + _t_diff_string + Style.RESET_ALL
                        desc_substring += _t_diff_string + " | "

                        # Seen At [ctime]
                        _t_last_string = "{:>20}".format(d_info['t_last'])
                        desc_substring += _t_last_string + " | "

                        # Value
                        _v_last_string = "{:>20}".format(d_info['v_last'])
                        desc_substring += _v_last_string

                        description_string += desc_substring + "\n"

            description_string += "\n"

        return description_string


def main(target, verbose=False):
    checker = DataChecker(target, verbose)
    checker.run()
    print(checker)
