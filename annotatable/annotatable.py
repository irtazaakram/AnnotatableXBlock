"""TO-DO: Write a description of what this XBlock is."""

import markupsafe
import textwrap
import pkg_resources
from django.utils import translation
from lxml import etree
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String
from xblockutils.resources import ResourceLoader

_ = lambda text: text


class AnnotatableXBlock(XBlock):
    """
    TO-DO: document what your XBlock does.
    """

    # Fields are defined on the class.  You can access them in your code as
    # self.<fieldname>.

    # TO-DO: delete count, and define your own fields.
    count = Integer(
        default=0,
        scope=Scope.user_state,
        help="A simple counter, to show something happening",
    )
    data = String(
        help=_("XML data for the annotation"),
        scope=Scope.content,
        default=textwrap.dedent(
            markupsafe.Markup(
                """
        <annotatable>
            <instructions>
                <p>Enter your (optional) instructions for the exercise in HTML format.</p>
                <p>Annotations are specified by an <code>{}annotation{}</code> tag which may may have the following attributes:</p>
                <ul class="instructions-template">
                    <li><code>title</code> (optional). Title of the annotation. Defaults to <i>Commentary</i> if omitted.</li>
                    <li><code>body</code> (<b>required</b>). Text of the annotation.</li>
                    <li><code>problem</code> (optional). Numeric index of the problem associated with this annotation. This is a zero-based index, so the first problem on the page would have <code>problem="0"</code>.</li>
                    <li><code>highlight</code> (optional). Possible values: yellow, red, orange, green, blue, or purple. Defaults to yellow if this attribute is omitted.</li>
                </ul>
            </instructions>
            <p>Add your HTML with annotation spans here.</p>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. <annotation title="My title" body="My comment" highlight="yellow" problem="0">Ut sodales laoreet est, egestas gravida felis egestas nec.</annotation> Aenean at volutpat erat. Cras commodo viverra nibh in aliquam.</p>
            <p>Nulla facilisi. <annotation body="Basic annotation example." problem="1">Pellentesque id vestibulum libero.</annotation> Suspendisse potenti. Morbi scelerisque nisi vitae felis dictum mattis. Nam sit amet magna elit. Nullam volutpat cursus est, sit amet sagittis odio vulputate et. Curabitur euismod, orci in vulputate imperdiet, augue lorem tempor purus, id aliquet augue turpis a est. Aenean a sagittis libero. Praesent fringilla pretium magna, non condimentum risus elementum nec. Pellentesque faucibus elementum pharetra. Pellentesque vitae metus eros.</p>
        </annotatable>
        """
            ).format(markupsafe.escape("<"), markupsafe.escape(">"))
        ),
    )

    HIGHLIGHT_COLORS = ["yellow", "orange", "purple", "blue", "green"]

    def _get_annotation_class_attr(self, index, el):
        """
        Returns a dict with the CSS class attribute to set on the annotation
        and an XML key to delete from the element.
        """

        attr = {}
        cls = ["annotatable-span", "highlight"]
        highlight_key = "highlight"
        color = el.get(highlight_key)

        if color is not None:
            if color in self.HIGHLIGHT_COLORS:
                cls.append("highlight-" + color)
            attr["_delete"] = highlight_key
        attr["value"] = " ".join(cls)

        return {"class": attr}

    def _get_annotation_data_attr(self, index, el):
        """
        Returns a dict in which the keys are the HTML data attributes
        to set on the annotation element. Each data attribute has a
        corresponding 'value' and (optional) '_delete' key to specify
        an XML attribute to delete.
        """

        data_attrs = {}
        attrs_map = {
            "body": "data-comment-body",
            "title": "data-comment-title",
            "problem": "data-problem-id",
        }

        for xml_key in attrs_map.keys():
            if xml_key in el.attrib:
                value = el.get(xml_key, "")
                html_key = attrs_map[xml_key]
                data_attrs[html_key] = {"value": value, "_delete": xml_key}

        return data_attrs

    def _render_annotation(self, index, el):
        """
        Renders an annotation element for HTML output.
        """
        attr = {}
        attr.update(self._get_annotation_class_attr(index, el))
        attr.update(self._get_annotation_data_attr(index, el))

        el.tag = "span"

        for key in attr.keys():
            el.set(key, attr[key]["value"])
            if "_delete" in attr[key] and attr[key]["_delete"] is not None:
                delete_key = attr[key]["_delete"]
                del el.attrib[delete_key]

    def _render_content(self):
        """
        Renders annotatable content with annotation spans and returns HTML.
        """

        xmltree = etree.fromstring(self.data)
        content = etree.tostring(xmltree, encoding="unicode")

        xmltree = etree.fromstring(content)
        xmltree.tag = "div"
        if "display_name" in xmltree.attrib:
            del xmltree.attrib["display_name"]

        index = 0
        for el in xmltree.findall(".//annotation"):
            self._render_annotation(index, el)
            index += 1

        return etree.tostring(xmltree, encoding="unicode")

    def _extract_instructions(self, xmltree):
        """
        Removes <instructions> from the xmltree and returns them as a string, otherwise None.
        """
        instructions = xmltree.find("instructions")
        if instructions is not None:
            instructions.tag = "div"
            xmltree.remove(instructions)
            return etree.tostring(instructions, encoding="unicode")
        return None

    def get_html(self):
        """
        Renders parameters to template.
        """

        xmltree = etree.fromstring(self.data)
        instructions = self._extract_instructions(xmltree)

        context = {
            "display_name": self.display_name,
            "element_id": self.location.html_id(),
            "instructions_html": instructions,
            "content_html": self._render_content(),
        }

        return self.runtime.service(self, "mako").render_lms_template(
            "annotatable.html", context
        )

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    # TO-DO: change this view to display your data your own way.
    def student_view(self, context=None):
        """
        Create primary view of the AnnotatableXBlock, shown to students when viewing courses.
        """
        if context:
            pass  # TO-DO: do something based on the context.
        html = self.resource_string("static/html/annotatable.html")
        frag = Fragment(html.format(self=self))
        frag.add_css(self.resource_string("static/css/annotatable.css"))

        # Add i18n js
        statici18n_js_url = self._get_statici18n_js_url()
        if statici18n_js_url:
            frag.add_javascript_url(
                self.runtime.local_resource_url(self, statici18n_js_url)
            )

        frag.add_javascript(self.resource_string("static/js/src/annotatable.js"))
        frag.initialize_js("AnnotatableXBlock")
        return frag

    def studio_view(self, _context):
        """
        Return the studio view.
        """
        fragment = Fragment(
            self.runtime.service(self, 'mako').render_cms_template(self.mako_template, self.get_context())
        )
        add_sass_to_fragment(fragment, 'AnnotatableBlockEditor.scss')
        add_webpack_js_to_fragment(fragment, 'AnnotatableBlockEditor')
        shim_xmodule_js(fragment, self.studio_js_module_name)
        return fragment


    # TO-DO: change this handler to perform your own actions.  You may need more
    # than one handler, or you may not need any handlers at all.
    @XBlock.json_handler
    def increment_count(self, data, suffix=""):
        """
        Increments data. An example handler.
        """
        if suffix:
            pass  # TO-DO: Use the suffix when storing data.
        # Just to show data coming in...
        assert data["hello"] == "world"

        self.count += 1
        return {"count": self.count}

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """Create canned scenario for display in the workbench."""
        return [
            (
                "AnnotatableXBlock",
                """<annotatable-xblock/>
            """,
            ),
            (
                "Multiple AnnotatableXBlock",
                """<vertical_demo>
                <annotatable-xblock/>
                <annotatable-xblock/>
                <annotatable-xblock/>
                </vertical_demo>
            """,
            ),
        ]

    @staticmethod
    def _get_statici18n_js_url():
        """
        Return the Javascript translation file for the currently selected language, if any.

        Defaults to English if available.
        """
        locale_code = translation.get_language()
        if locale_code is None:
            return None
        text_js = "public/js/translations/{locale_code}/text.js"
        lang_code = locale_code.split("-")[0]
        for code in (locale_code, lang_code, "en"):
            loader = ResourceLoader(__name__)
            if pkg_resources.resource_exists(
                loader.module_name, text_js.format(locale_code=code)
            ):
                return text_js.format(locale_code=code)
        return None

    @staticmethod
    def get_dummy():
        """
        Generate initial i18n with dummy method.
        """
        return translation.gettext_noop("Dummy")
