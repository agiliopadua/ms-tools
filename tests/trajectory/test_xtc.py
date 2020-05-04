#!/usr/bin/env python3

import os
import pytest
from mstools.topology import Topology
from mstools.trajectory import Trajectory

cwd = os.path.dirname(os.path.abspath(__file__))

top = Topology.open(cwd + '/files/100-SPCE.psf')
omm_top = top.to_omm_topology()
top = Topology()
top.init_from_omm_topology(omm_top)


def test_read():
    xtc = Trajectory.open(cwd + '/files/100-SPCE.xtc')
    assert xtc.n_atom == 300
    assert xtc.n_frame == 4


def test_write():
    gro = Trajectory.open(cwd + '/files/100-SPCE.gro')
    xtc = Trajectory.open(cwd + '/files/gro-out.xtc', 'w')

    for i in range(gro.n_frame):
        frame = gro.read_frame(i)
        xtc.write_frame(frame)
