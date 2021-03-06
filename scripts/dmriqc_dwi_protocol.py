#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import shutil

import numpy as np
from scilpy.utils.bvec_bval_tools import identify_shells
from scilpy.viz.gradient_sampling import build_ms_from_shell_idx

from dmriqcpy.analysis.utils import dwi_protocol
from dmriqcpy.io.report import Report
from dmriqcpy.io.utils import (add_overwrite_arg, assert_inputs_exist,
                               assert_outputs_exist)
from dmriqcpy.viz.graph import (graph_directions_per_shells, graph_dwi_protocol,
                                graph_subjects_per_shells)
from dmriqcpy.viz.screenshot import plot_proj_shell
from dmriqcpy.viz.utils import analyse_qa, dataframe_to_html

DESCRIPTION = """
Compute DWI protocol report.
"""


def _build_arg_parser():
    p = argparse.ArgumentParser(description=DESCRIPTION,
                                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('output_report',
                   help='Filename of QC report (in html format).')

    p.add_argument('--bval', nargs='+', required=True,
                   help='List of bval files.')

    p.add_argument('--bvec', nargs='+', required=True,
                   help='List of bvec files.')

    p.add_argument('--tolerance', '-t',
                   metavar='INT', type=int, default=20,
                   help='The tolerated gap between the b-values to '
                        'extract\nand the actual b-values.')

    add_overwrite_arg(p)

    return p


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    if not len(args.bval) == len(args.bvec):
        parser.error("Not the same number of images in input.")

    all_data = np.concatenate([args.bval,
                               args.bvec])
    assert_inputs_exist(parser, all_data)
    assert_outputs_exist(parser, args, [args.output_report, "data", "libs"])

    if os.path.exists("data"):
        shutil.rmtree("data")
    os.makedirs("data")

    if os.path.exists("libs"):
        shutil.rmtree("libs")

    name = "DWI Protocol"
    summary, stats_for_graph, stats_all, shells = dwi_protocol(args.bval)
    warning_dict = {}
    warning_dict[name] = analyse_qa(stats_for_graph, stats_all,
                                    ["Nbr shells", "Nbr directions"])
    warning_images = [filenames for filenames in warning_dict[name].values()]
    warning_list = np.concatenate(warning_images)
    warning_dict[name]['nb_warnings'] = len(np.unique(warning_list))

    stats_html = dataframe_to_html(stats_all)
    summary_dict = {}
    summary_dict[name] = stats_html

    graphs = []
    graphs.append(
        graph_directions_per_shells("Nbr directions per shell", shells))
    graphs.append(graph_subjects_per_shells("Nbr subjects per shell", shells))
    for c in ["Nbr shells", "Nbr directions"]:
        graph = graph_dwi_protocol(c, c, stats_for_graph)
        graphs.append(graph)

    subjects_dict = {}
    for bval, bvec in zip(args.bval, args.bvec):
        filename = os.path.basename(bval)
        subjects_dict[bval] = {}
        points = np.genfromtxt(bvec)
        if points.shape[0] == 3:
            points = points.T
        bvals = np.genfromtxt(bval)
        centroids, shell_idx = identify_shells(bvals)
        ms = build_ms_from_shell_idx(points, shell_idx)
        plot_proj_shell(ms, centroids, use_sym=True, use_sphere=True,
                        same_color=False, rad=0.025, opacity=0.2,
                        ofile=os.path.join("data", name + filename),
                        ores=(800, 800))
        subjects_dict[bval]['screenshot'] = os.path.join("data",
                                                         name + filename + '.png')
    metrics_dict = {}
    for subj in args.bval:
        summary_html = dataframe_to_html(summary[subj])
        subjects_dict[subj]['stats'] = summary_html
    metrics_dict[name] = subjects_dict

    nb_subjects = len(args.bval)
    report = Report(args.output_report)
    report.generate(title="Quality Assurance DWI protocol",
                    nb_subjects=nb_subjects, metrics_dict=metrics_dict,
                    summary_dict=summary_dict, graph_array=graphs,
                    warning_dict=warning_dict)


if __name__ == '__main__':
    main()
