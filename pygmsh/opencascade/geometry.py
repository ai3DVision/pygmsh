# -*- coding: utf-8 -*-
#
from ..__about__ import __version__
from ..helpers import get_gmsh_major_version, _is_string

from .ball import Ball
from .box import Box
from .cylinder import Cylinder
from .disk import Disk
from .dummy import Dummy
from .line_base import LineBase
from .rectangle import Rectangle
from .surface_base import SurfaceBase
from .torus import Torus
from .volume_base import VolumeBase


class Geometry(object):
    def __init__(
            self,
            characteristic_length_min=None,
            characteristic_length_max=None
            ):
        self._BOOLEAN_ID = 0
        self._EXTRUDE_ID = 0
        self._GMSH_MAJOR = get_gmsh_major_version()
        self._GMSH_CODE = [
            '// This code was created by PyGmsh v{}.'.format(__version__),
            'SetFactory("OpenCASCADE");',
            ]

        if characteristic_length_min is not None:
            self._GMSH_CODE.append(
                'Mesh.CharacteristicLengthMin = {};'.format(
                    characteristic_length_min
                    ))

        if characteristic_length_max is not None:
            self._GMSH_CODE.append(
                'Mesh.CharacteristicLengthMax = {};'.format(
                    characteristic_length_max
                    ))
        return

    def get_code(self):
        '''Returns properly formatted Gmsh code.
        '''
        return '\n'.join(self._GMSH_CODE)

    def get_gmsh_major(self):
        '''Return the major version of the gmsh executable.
        '''
        return self._GMSH_MAJOR

    def add_rectangle(self, *args, **kwargs):
        p = Rectangle(*args, **kwargs)
        self._GMSH_CODE.append(p.code)
        return p

    def add_disk(self, *args, **kwargs):
        p = Disk(*args, **kwargs)
        self._GMSH_CODE.append(p.code)
        return p

    def add_ball(self, *args, **kwargs):
        p = Ball(*args, **kwargs)
        self._GMSH_CODE.append(p.code)
        return p

    def add_box(self, *args, **kwargs):
        p = Box(*args, **kwargs)
        self._GMSH_CODE.append(p.code)
        return p

    def add_cylinder(self, *args, **kwargs):
        p = Cylinder(*args, **kwargs)
        self._GMSH_CODE.append(p.code)
        return p

    def add_torus(self, *args, **kwargs):
        p = Torus(*args, **kwargs)
        self._GMSH_CODE.append(p.code)
        return p

    # pylint: disable=too-many-branches
    def _boolean_operation(
            self,
            operation,
            input_entities,
            tool_entities,
            delete=True
            ):
        '''Boolean operations, see
        http://gmsh.info/doc/texinfo/gmsh.html#Boolean-operations input_entity
        and tool_entity are called object and tool in gmsh documentation.
        '''
        self._BOOLEAN_ID += 1

        # assert that all entities are of the same dimensionality
        dim_type = None
        legal_dim_types = {
            LineBase: 'Line',
            SurfaceBase: 'Surface',
            VolumeBase: 'Volume',
            }
        for ldt in legal_dim_types.keys():
            if isinstance(input_entities[0], ldt):
                dim_type = ldt
                break
        assert dim_type is not None, \
            'Illegal input type \'{}\' for Boolean operation.'.format(
                type(input_entities[0])
                )
        for e in input_entities[1:] + tool_entities:
            assert isinstance(e, dim_type), \
                'Incompatible input type \'{}\' for Boolean operation.'.format(
                    type(e)
                    )

        name = 'bo{}'.format(self._BOOLEAN_ID)
        self._GMSH_CODE.append(
            '{}[] = {}{{{} {{{}}}; {}}} {{{} {{{}}}; {}}};'
            .format(
                name,
                operation,
                legal_dim_types[dim_type],
                ','.join(e.id for e in input_entities),
                'Delete;' if delete else '',
                legal_dim_types[dim_type],
                ','.join(e.id for e in tool_entities),
                'Delete;' if delete else ''
                ))

        return dim_type(id0=name, is_list=True)

    def boolean_intersection(self, entities, delete=True):
        '''Boolean intersection, see
        http://gmsh.info/doc/texinfo/gmsh.html#Boolean-operations input_entity
        and tool_entity are called object and tool in gmsh documentation.
        '''
        assert len(entities) > 1
        return self._boolean_operation(
                'BooleanIntersection',
                [entities[0]], entities[1:], delete=delete
                )

    def boolean_union(self, entities, delete=True):
        '''Boolean union, see http://gmsh.info/doc/texinfo/gmsh.html#Boolean-operations
        input_entity and tool_entity are called object and tool in gmsh
        documentation.
        '''
        return self._boolean_operation(
                'BooleanUnion',
                [entities[0]], entities[1:], delete=delete
                )

    def boolean_difference(self, *args, **kwargs):
        '''Boolean difference, see
        http://gmsh.info/doc/texinfo/gmsh.html#Boolean-operations input_entity
        and tool_entity are called object and tool in gmsh documentation.
        '''
        return self._boolean_operation('BooleanDifference', *args, **kwargs)

    def boolean_fragments(self, *args, **kwargs):
        '''Boolean fragments, see
        http://gmsh.info/doc/texinfo/gmsh.html#Boolean-operations input_entity
        and tool_entity are called object and tool in gmsh documentation.
        '''
        return self._boolean_operation('BooleanFragments', *args, **kwargs)

    def extrude(
            self,
            input_entity,
            translation_axis
            ):
        '''Extrusion (translation + rotation) of any entity along a given
        translation_axis, around a given rotation_axis, about a given angle. If
        one of the entities is not provided, this method will produce only
        translation or rotation.
        '''
        self._EXTRUDE_ID += 1

        if _is_string(input_entity):
            entity = Dummy(input_entity)
        elif isinstance(input_entity, SurfaceBase):
            entity = Dummy('Surface{{{}}}'.format(input_entity.id))
        elif hasattr(input_entity, 'surface'):
            entity = Dummy('Surface{{{}}}'.format(input_entity.surface.id))
        else:
            assert isinstance(input_entity, LineBase), \
                'Illegal extrude entity.'
            entity = Dummy('Line{{{}}}'.format(input_entity.id))

        # out[] = Extrude{0,1,0}{ Line{1}; };
        name = 'ex{}'.format(self._EXTRUDE_ID)

        # Only translation
        self._GMSH_CODE.append(
            '{}[] = Extrude{{{}}}{{{};}};'.format(
                name,
                ','.join(repr(x) for x in translation_axis),
                entity.id
            ))

        # From <http://www.manpagez.com/info/gmsh/gmsh-2.4.0/gmsh_66.php>:
        #
        # > In this last extrusion command we retrieved the volume number
        # > programatically by saving the output of the command into a
        # > list. This list will contain the "top" of the extruded surface (in
        # > out[0]) as well as the newly created volume (in out[1]).
        #
        top = '{}[0]'.format(name)
        extruded = '{}[1]'.format(name)

        if isinstance(input_entity, LineBase):
            top = LineBase(top)
            # A surface extruded from a single line has always 4 edges
            extruded = SurfaceBase(extruded)
        elif isinstance(input_entity, SurfaceBase):
            top = SurfaceBase(top)
            extruded = VolumeBase(extruded)
        else:
            top = Dummy(top)
            extruded = Dummy(extruded)

        return top, extruded
