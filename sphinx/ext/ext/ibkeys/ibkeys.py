### Copyright 2014, MTA SZTAKI, www.sztaki.hu
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###    http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
# Extension for Sphinx to document Info Broker keys

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx.util.nodes import nested_parse_with_titles
from sphinx import addnodes
from sphinx.util.nodes import set_source_info

def update_attrs(self, directive):
    self.document = directive.state.document
    self['domain'] = directive.domain
    self['objtype'] = self['desctype'] = directive.objtype
    self['noindex'] = ('noindex' in directive.options)
    self['first'] = False

def visit_declibkey_node(self, node): self.visit_raw(node)
def depart_declibkey_node(self, node): self.depart_raw(node)
class declibkey(nodes.General, nodes.Element):
    pass

def visit_keynode_node(self, node): self.visit_literal(node)
def depart_keynode_node(self, node): self.depart_literal(node)
class keynode(nodes.literal):
    def __init__(self, key):
        super(keynode, self).__init__(key, key)

def visit_keydoc_node(self, node): self.visit_desc_content(node)
def depart_keydoc_node(self, node): self.depart_desc_content(node)
class keydoc(addnodes.desc_content):
    def __init__(self, state, content):
        super(keydoc, self).__init__('\n'.join(content))
        nested_parse_with_titles(state, content, self)

def visit_ibkey_node(self, node): self.visit_desc(node)
def depart_ibkey_node(self, node): self.depart_desc(node)
class ibkey(addnodes.desc):
    def __init__(self, directive, refkey, key_elem, doc):
        label = nodes.strong('@provides', '@provides')
        sep = nodes.Text(': ', ': ')
        par = addnodes.desc_signature('<autodoc>', '', label, sep, key_elem)
        update_attrs(par, directive)
        self.name = 'py:ibkey'

        super(ibkey, self).__init__()
        self += par
        self += doc
        update_attrs(self, directive)

def visit_iblist_entry_node(self, node): self.visit_desc(node)
def depart_iblist_entry_node(self, node): self.depart_desc(node)
class iblist_entry(addnodes.desc):
    def __init__(self, directive, env, docname,
                 source_class, source_file, lineno,
                 refkey, key_elem, doc):
        filename = env.doc2path(docname, base=None)
        linktext = "{0} ({1}:{2})".format(source_class, source_file, lineno)
        refnode = nodes.reference('', '', nodes.emphasis(linktext, linktext))
        refnode['refdocname'] = docname
        refnode['refuri'] = "{0}#{1}".format(
            env.app.builder.get_target_uri(docname), refkey)

        origentry = nodes.inline('', '',
                                 nodes.Text(' (', ' ('),
                                 refnode,
                                 nodes.Text(')', ')'))

        entry_header = addnodes.desc_signature('', '', key_elem, origentry)
        entry_content = doc

        super(iblist_entry, self).__init__('', entry_header, entry_content)
        update_attrs(self, directive)

class ibkeylist(addnodes.desc_content):
    pass

class dummy(nodes.Admonition, nodes.Element): pass
def visit_dummy_node(self, node): self.visit_admonition(node)
def depart_dummy_node(self, node): self.depart_admonition(node)

class DeclIBKey(Directive):
    has_content = True

    def run(self):
        # The declared key is valid in the scope of the parent docstring.
        self.content.parent.declared_ibkey = self.content[0]
        return []

class IBKeyListDirective(Directive):
    def run(self):
        return [ibkeylist('')]

from sphinx.util.docfields import DocFieldTransformer
#from sphinx.directives import ObjectDescription
from sphinx.domains.python import PyObject
from sphinx.util.compat import make_admonition

class IBKeyDirective(PyObject):
    has_content = True
    doc_field_types = PyObject.doc_field_types
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}

    def find_key(self, parent):
        if hasattr(parent, 'declared_ibkey'):
            return parent.declared_ibkey
        elif hasattr(parent, 'parent'):
            return self.find_key(parent.parent)
        else:
            raise Exception(
                'There is no declared key in the scope of this directive.')

    def run(self):
        document = self.state.document
        env = document.settings.env
        docname = env.docname

        if ':' in self.name:
            self.domain, self.objtype = self.name.split(':', 1)
        else:
            self.domain, self.objtype = 'py', self.name

        key = self.find_key(self.content.parent)

        targetnode = nodes.target('', '', ids=[key])

        key_elem = keynode(key)

        # Separating argument and content causes two <dd>-s to be generated in
        # the same <dl>
        doc = addnodes.desc_content()
        update_attrs(doc, self)
        txt = '\n'.join(self.arguments)
        self.before_content()
        details = keydoc(self.state, self.content)
        update_attrs(details, self)
        DocFieldTransformer(self).transform_all(details)
        self.after_content()
        doc += nodes.paragraph(txt, txt)
        doc += details

        import os
        source_line = self.lineno
        source, _ = self.state_machine.get_source_and_line(source_line)
        src_file, src_other = source.split(':', 1)
        source_file = os.path.basename(src_file)

        doc_entry = ibkey(self, key, key_elem, doc)
        #doc_entry = make_admonition(dummy, self.name, 'Alma', self.options, self.content, self.lineno, self.content_offset, self.block_text, self.state, self.state_machine)[0]
        
        catalog_entry = iblist_entry(
            self,
            env, docname, src_other, source_file, source_line,
            key, key_elem, doc)

        set_source_info(self, doc_entry)
        set_source_info(self, catalog_entry)
        env.resolve_references(doc_entry, docname, env.app.builder)
        env.resolve_references(catalog_entry, docname, env.app.builder)

        if not hasattr(env, 'ibkey_all_ibkeys'):
            env.ibkey_all_ibkeys = dict()

        env.ibkey_all_ibkeys[key] = dict(docname=docname,
                                         catalog_entry=catalog_entry)

        # - super.run() doesnt't kill the structure, it works fine
        # - returning both superrun and doc_entry does (in any order)
        # - The todo in the method docstring is rendered outside the 
        #   method's documentation (?!)
        return [doc_entry] #[targetnode, doc_entry]

def purge_ibkeys(app, env, docname):
    if not hasattr(env, 'ibkey_all_ibkeys'):
        return

    env.ibkey_all_ibkeys = dict((k, v)
                                for k, v in env.ibkey_all_ibkeys.iteritems()
                                if v['docname'] != docname)

def process_ibkey_nodes(app, doctree, fromdocname):
    env = app.builder.env

    for node in doctree.traverse(ibkeylist):
        content = list()

        all_ibkeys = getattr(env, 'ibkey_all_ibkeys', dict())

        for key in sorted(all_ibkeys.iterkeys()):
            content.append(all_ibkeys[key]['catalog_entry'])

        node.replace_self(content)


def setup(app):
    app.add_node(ibkeylist)
    g = globals()

    for nodename in ['ibkey', 'keydoc', 'declibkey', 'iblist_entry',
                     'keynode', 'dummy']:
        methods = tuple(g['{1}_{0}_node'.format(nodename, role)]
                        for role in ['visit', 'depart'])
        allmethods = dict((k,methods) for k in ['html', 'latex', 'text'])
        app.add_node(g[nodename], **allmethods)

    app.add_directive('ibkey', IBKeyDirective)
    app.add_directive('decl_ibkey', DeclIBKey)
    app.add_directive('ibkeylist', IBKeyListDirective)

    app.connect('doctree-resolved', process_ibkey_nodes)
    app.connect('env-purge-doc', purge_ibkeys)
