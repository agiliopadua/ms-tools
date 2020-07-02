import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
from .forcefield import ForceField
from .ffterm import *


class Zfp():
    '''
    Load ForceField from ZFP file.

    ZFP is the default format for storing ForceField in mstools.
    XML language is used by ZFP file to serialize the setting and all the FFTerms in a ForceField object.
    An example is given in the examples folder.

    Several files can be read at one time.
    Only one ForceField object will be created and it will contain force field terms from all of the files.
    Note that the settings of the ForceField is read from the first file.
    The settings in other files will be ignored.

    A force field term describing one topology element should only appear once.
    If there are duplicated terms, an Exception will be raised.
    e.g. HarmonicAngleTerm('c_4', 'c_4', 'h_1') and SDKAngleTerm('c_4', 'c_4', 'h_1') are considered as duplicated,
    because both of them are describing the angle type ('c_4', 'c_4', 'h_1').
    LJ126Term('c_4', 'h_1') and MieTerm('c_4', 'h_1') are also duplicated,
    because both of them are describing the vdW interactions between atom types 'c_4' and 'h_1'.

    Parameters
    ----------
    files : list of str

    Attributes
    ----------
    forcefield : ForceField
    '''

    def __init__(self, *files):
        self.forcefield = ForceField()
        self._setting_read = False
        for file in files:
            self._parse(file)

    def _parse(self, file):
        try:
            tree = ET.ElementTree(file=file)
        except:
            raise Exception('Invalid ZFP file')

        root = tree.getroot()
        if root is None:
            raise Exception('Empty ZFP file')

        ff = self.forcefield

        if not self._setting_read:
            node = root.find('Setting')
            ff.vdw_cutoff = float(node.attrib['vdw_cutoff'])
            ff.vdw_long_range = node.attrib['vdw_long_range']
            ff.lj_mixing_rule = node.attrib['lj_mixing_rule']
            ff.scale_14_vdw = float(node.attrib['scale_14_vdw'])
            ff.scale_14_coulomb = float(node.attrib['scale_14_coulomb'])
            self._setting_read = True

        tags = {
            'AtomTypes'           : ff.atom_types,
            'ChargeIncrementTerms': ff.charge_increment_terms,
            'VdwTerms'            : ff.vdw_terms,
            'PairwiseVdwTerms'    : ff.pairwise_vdw_terms,
            'BondTerms'           : ff.bond_terms,
            'AngleTerms'          : ff.angle_terms,
            'DihedralTerms'       : ff.dihedral_terms,
            'ImproperTerms'       : ff.improper_terms,
            'PolarizableTerms'    : ff.polarizable_terms,
        }
        for tag, d in tags.items():
            node = root.find(tag)
            if node is None:
                continue
            for element in node:
                try:
                    cls = getattr(sys.modules['mstools.forcefield.ffterm'], element.tag)
                except:
                    raise Exception('Invalid tag %s' % element.tag)
                term = cls.from_zfp(element.attrib)
                if term.name in d.keys():
                    raise Exception('Duplicated term: %s' % str(term))
                d[term.name] = term

    @staticmethod
    def save_to(ff, file):
        '''
        Save ForceField to a ZFP file

        Parameters
        ----------
        ff : ForceField
        file : str
        '''
        root = ET.Element('ForceFieldTerms')

        attrib = {
            'vdw_cutoff'      : str(ff.vdw_cutoff),
            'vdw_long_range'  : ff.vdw_long_range,
            'lj_mixing_rule'  : ff.lj_mixing_rule,
            'scale_14_vdw'    : str(ff.scale_14_vdw),
            'scale_14_coulomb': str(ff.scale_14_coulomb),
        }
        node = ET.SubElement(root, 'Setting', attrib=attrib)

        tags = {
            'AtomTypes'           : ff.atom_types,
            'ChargeIncrementTerms': ff.charge_increment_terms,
            'VdwTerms'            : ff.vdw_terms,
            'PairwiseVdwTerms'    : ff.pairwise_vdw_terms,
            'BondTerms'           : ff.bond_terms,
            'AngleTerms'          : ff.angle_terms,
            'DihedralTerms'       : ff.dihedral_terms,
            'ImproperTerms'       : ff.improper_terms,
            'PolarizableTerms'    : ff.polarizable_terms,
        }
        for tag, d in tags.items():
            node = ET.SubElement(root, tag)
            for term in d.values():
                ET.SubElement(node, term.__class__.__name__, attrib=term.to_zfp())

        str_xml = minidom.parseString(ET.tostring(root)).toprettyxml(indent='  ')
        with open(file, 'w') as f:
            f.write(str_xml)
