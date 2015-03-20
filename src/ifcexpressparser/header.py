###############################################################################
#                                                                             #
# This file is part of IfcOpenShell.                                          #
#                                                                             #
# IfcOpenShell is free software: you can redistribute it and/or modify        #
# it under the terms of the Lesser GNU General Public License as published by #
# the Free Software Foundation, either version 3.0 of the License, or         #
# (at your option) any later version.                                         #
#                                                                             #
# IfcOpenShell is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                #
# Lesser GNU General Public License for more details.                         #
#                                                                             #
# You should have received a copy of the Lesser GNU General Public License    #
# along with this program. If not, see <http://www.gnu.org/licenses/>.        #
#                                                                             #
###############################################################################

import templates
import documentation

class Header:
    def __init__(self, mapping):
        declarations = []

        write = lambda str, **kwargs: declarations.append(str%dict({
            'documentation': templates.multi_line_comment(documentation.description(kwargs['name']))}, **kwargs))
            
        forward_names = list(mapping.schema.entities.keys()) + list(mapping.schema.simpletypes.keys())
        forward_definitions = "".join(["class %s; "%n for n in forward_names])
        
        for name, type in mapping.schema.selects.items():
            write(templates.select, name=name)

        for name, type in mapping.schema.enumerations.items():
            short_name = name[:-4] if name.endswith("Enum") else name
            write(templates.enumeration, name=name, values=", ".join(["%s_%s"%(short_name, v) for v in type.values]))
        
        emitted_simpletypes = set()
        while len(emitted_simpletypes) < len(mapping.schema.simpletypes):
            for name, type in mapping.schema.simpletypes.items():
                if name in emitted_simpletypes: continue
                type_str = mapping.make_type_string(mapping.flatten_type_string(type))
                attr_type = mapping.make_argument_type(type)
                superclass = mapping.simple_type_parent(name)
                if superclass is None: 
                    superclass = "IfcUtil::IfcBaseType"
                elif superclass not in emitted_simpletypes:
                    continue
                emitted_simpletypes.add(name)
                write(templates.simpletype, name=name, type=type_str, attr_type=attr_type, superclass=superclass)

        class_definitions = []

        write = lambda str, **kwargs: class_definitions.append(str%dict({
            'documentation': templates.multi_line_comment(documentation.description(kwargs['name']))}, **kwargs))

        emitted_entities = set()
        while len(emitted_entities) < len(mapping.schema.entities):
            for name, type in mapping.schema.entities.items():
                if name in emitted_entities: continue
                if len(type.supertypes) == 0 or set(type.supertypes) < emitted_entities:
                    attr_lines = []
                    def write_method(attr):
                        attr_lines.extend(["/// %s"%d for d in documentation.description((name, attr.name))])
                        type_str = mapping.get_parameter_type(attr, allow_optional=True, allow_entities=True)
                        if mapping.make_argument_type(attr) != "IfcUtil::Argument_UNKNOWN":
                            attr_lines.append("%s %s() const;"%(type_str, attr.name))
                            attr_lines.append("void %s(%s v);"%(attr.name, type_str))

                    [write_method(attr) for attr in type.attributes]

                    inv_lines = []
                    def write_inverse(attr):
                        inv_lines.append(templates.inverse_attr%{'name':attr.name, 'entity':attr.entity, 'attribute':attr.attribute})

                    if type.inverse:
                        [write_inverse(attr) for attr in type.inverse.elements]

                    attributes = "\n".join(["%s%s"%(' '*4, a) for a in attr_lines])
                    if len(attributes): attributes += '\n'

                    inverse = "\n".join(["%s%s"%(' '*4, a) for a in inv_lines])
                    if len(inverse): inverse += '\n'

                    supertypes = type.supertypes if len(type.supertypes) else ['IfcUtil::IfcBaseEntity']
                    superclass = ": %s "%(", ".join(["public %s"%c for c in supertypes]))

                    argument_count = mapping.argument_count(type)

                    argument_start = argument_count - len(type.attributes)

                    argument_name_function_body_switch_stmt = " switch (i) {%s}"%("".join(['case %d: return "%s"; '%(i+argument_start, attr.name) for i, attr in enumerate(type.attributes)])) if len(type.attributes) else ""
                    argument_name_function_body_tail = (" return %s::getArgumentName(i); "%type.supertypes[0]) if len(type.supertypes) == 1 else ' throw IfcParse::IfcException("argument out of range"); '

                    argument_name_function_body = argument_name_function_body_switch_stmt + argument_name_function_body_tail

                    argument_type_function_body_switch_stmt = " switch (i) {%s}"%("".join(['case %d: return %s; '%(i+argument_start, mapping.make_argument_type(attr)) for i, attr in enumerate(type.attributes)])) if len(type.attributes) else ""
                    argument_type_function_body_tail = (" return %s::getArgumentType(i); "%type.supertypes[0]) if len(type.supertypes) == 1 else ' throw IfcParse::IfcException("argument out of range"); '

                    argument_type_function_body = argument_type_function_body_switch_stmt + argument_type_function_body_tail
                    
                    argument_entity_function_body_switch_stmt = " switch (i) {%s}"%("".join(['case %d: return %s; '%(i+argument_start, mapping.make_argument_entity(attr)) for i, attr in enumerate(type.attributes)])) if len(type.attributes) else ""
                    argument_entity_function_body_tail = (" return %s::getArgumentEntity(i); "%type.supertypes[0]) if len(type.supertypes) == 1 else ' throw IfcParse::IfcException("argument out of range"); '

                    argument_entity_function_body = argument_entity_function_body_switch_stmt + argument_entity_function_body_tail

                    constructor_arguments = ", ".join("%(full_type)s v%(index)d_%(name)s"%a for a in mapping.get_assignable_arguments(type))

                    write(templates.entity, **locals())
                    emitted_entities.add(name)

        self.str = templates.header % {
            'schema_name_upper'   : mapping.schema.name.upper(),
            'schema_name'         : mapping.schema.name.capitalize(),
            'declarations'        : ''.join(declarations),
            'forward_definitions' : forward_definitions,
            'class_definitions'   : ''.join(class_definitions)
        }

        self.schema_name = mapping.schema.name.capitalize()
    def __repr__(self):
        return self.str
    def emit(self):
        f = open('%s.h'%self.schema_name, 'w', encoding='utf-8')
        f.write(str(self))
        f.close()

