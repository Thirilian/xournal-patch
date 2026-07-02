#!/usr/bin/env python3
"""
Corrige les warnings de compilation identifies dans les logs de build, sur
une base Xournal++ non modifiee. Aucun changement de comportement :
- Les warnings de conversion numerique (-Wconversion/-Wfloat-conversion) sont
  corriges avec un static_cast explicite documentant une conversion deja
  existante implicitement.
- Les warnings d'API depreciee (-Wdeprecated-declarations) sont supprimes
  localement via des pragmas GCC/clang cibles, sans toucher au code genere
  (remplacer ces API impliquerait un risque reel de changement de
  comportement, cf. explication donnee en conversation).

A lancer depuis la racine du depot xournalpp, sur une copie non modifiee.
"""
import sys
from pathlib import Path


def apply_edit(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        if text.count(new) > 0:
            print(f"[SKIP]  {label}: déjà appliqué.")
            return True
        print(f"[ECHEC] {label}: motif introuvable dans {path}")
        return False
    if count > 1:
        print(f"[ECHEC] {label}: motif trouvé {count} fois dans {path} (doit être unique)")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[OK]    {label}")
    return True


PRAGMA_PUSH = (
    "#if defined(__GNUC__) || defined(__clang__)\n"
    "#pragma GCC diagnostic push\n"
    '#pragma GCC diagnostic ignored "-Wdeprecated-declarations"\n'
    "#endif\n"
)
PRAGMA_POP = "#if defined(__GNUC__) || defined(__clang__)\n#pragma GCC diagnostic pop\n#endif\n"


def main():
    ok = True

    # ================= Settings.cpp : -Wconversion (26 sites) =================
    f = Path("src/core/control/settings/Settings.cpp")
    if not f.exists():
        print(f"[ECHEC] {f} introuvable. Lancez ce script depuis la racine du dépôt xournalpp.")
        sys.exit(1)

    settings_edits = [
        (
            "this->displayDpi = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->displayDpi = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "displayDpi",
        ),
        (
            "this->mainWndWidth = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->mainWndWidth = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "mainWndWidth",
        ),
        (
            "this->mainWndHeight = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->mainWndHeight = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "mainWndHeight",
        ),
        (
            "this->sidebarWidth = std::max<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10), 50);",
            "this->sidebarWidth =\n"
            "                std::max<int>(static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10)), 50);",
            "sidebarWidth",
        ),
        (
            "this->numColumns = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->numColumns = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "numColumns",
        ),
        (
            "this->numRows = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->numRows = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "numRows",
        ),
        (
            "this->numPairsOffset = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->numPairsOffset = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "numPairsOffset",
        ),
        (
            "this->cursorHighlightColor = g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->cursorHighlightColor =\n"
            "                static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "cursorHighlightColor",
        ),
        (
            "this->cursorHighlightBorderColor = g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->cursorHighlightBorderColor =\n"
            "                static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "cursorHighlightBorderColor",
        ),
        (
            "this->selectionBorderColor = Color(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "this->selectionBorderColor =\n"
            "                Color(static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10)));",
            "selectionBorderColor",
        ),
        (
            "this->selectionMarkerColor = Color(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "this->selectionMarkerColor =\n"
            "                Color(static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10)));",
            "selectionMarkerColor",
        ),
        (
            "this->activeSelectionColor = Color(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "this->activeSelectionColor =\n"
            "                Color(static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10)));",
            "activeSelectionColor",
        ),
        (
            "this->recolorParameters.recolor =\n"
            "                Recolor(ColorU8(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10)),\n"
            "                        this->recolorParameters.recolor.getDark());",
            "this->recolorParameters.recolor =\n"
            "                Recolor(ColorU8(static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10))),\n"
            "                        this->recolorParameters.recolor.getDark());",
            "recolor.light",
        ),
        (
            "this->recolorParameters.recolor =\n"
            "                Recolor(this->recolorParameters.recolor.getLight(),\n"
            "                        ColorU8(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10)));",
            "this->recolorParameters.recolor =\n"
            "                Recolor(this->recolorParameters.recolor.getLight(),\n"
            "                        ColorU8(static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10))));",
            "recolor.dark",
        ),
        (
            "this->backgroundColor = Color(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "this->backgroundColor =\n"
            "                Color(static_cast<uint32_t>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10)));",
            "backgroundColor",
        ),
        (
            "this->autosaveTimeout = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->autosaveTimeout = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "autosaveTimeout",
        ),
        (
            "this->pdfPageCacheSize = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->pdfPageCacheSize = static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "pdfPageCacheSize",
        ),
        (
            "this->preloadPagesBefore = g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->preloadPagesBefore =\n"
            "                static_cast<unsigned int>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "preloadPagesBefore",
        ),
        (
            "this->preloadPagesAfter = g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->preloadPagesAfter =\n"
            "                static_cast<unsigned int>(g_ascii_strtoull(reinterpret_cast<const char*>(value), nullptr, 10));",
            "preloadPagesAfter",
        ),
        (
            "this->drawDirModsRadius = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->drawDirModsRadius =\n"
            "                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "drawDirModsRadius",
        ),
        (
            "this->defaultSeekTime = tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr);",
            "this->defaultSeekTime =\n"
            "                static_cast<unsigned int>(tempg_ascii_strtod(reinterpret_cast<const char*>(value), nullptr));",
            "defaultSeekTime",
        ),
        (
            "this->audioInputDevice = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->audioInputDevice =\n"
            "                static_cast<PaDeviceIndex>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "audioInputDevice",
        ),
        (
            "this->audioOutputDevice = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->audioOutputDevice =\n"
            "                static_cast<PaDeviceIndex>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "audioOutputDevice",
        ),
        (
            "this->numIgnoredStylusEvents =\n"
            "                std::max<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10), 0);",
            "this->numIgnoredStylusEvents = std::max<int>(\n"
            "                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10)), 0);",
            "numIgnoredStylusEvents",
        ),
        (
            "this->strokeFilterIgnoreTime = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->strokeFilterIgnoreTime =\n"
            "                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "strokeFilterIgnoreTime",
        ),
        (
            "this->strokeFilterSuccessiveTime = g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10);",
            "this->strokeFilterSuccessiveTime =\n"
            "                static_cast<int>(g_ascii_strtoll(reinterpret_cast<const char*>(value), nullptr, 10));",
            "strokeFilterSuccessiveTime",
        ),
        (
            "#define SAVE_UINT_PROP(var) xmlNode = savePropertyUnsigned((const char*)#var, var, root)",
            "#define SAVE_UINT_PROP(var) xmlNode = savePropertyUnsigned((const char*)#var, static_cast<unsigned int>(var), root)",
            "SAVE_UINT_PROP macro (stabilizerBuffersize)",
        ),
    ]
    for old, new, label in settings_edits:
        ok &= apply_edit(f, old, new, f"Settings.cpp: {label}")

    # ================= EraseHandler.h : LegacyRedrawable deprecated =================
    f = Path("src/core/control/tools/EraseHandler.h")
    ok &= apply_edit(
        f,
        old="class EraseHandler {\npublic:\n"
            "    EraseHandler(UndoRedoHandler* undo, Document* doc, const PageRef& page, ToolHandler* handler,\n"
            "                 LegacyRedrawable* view);\n"
            "    virtual ~EraseHandler();",
        new="class EraseHandler {\npublic:\n"
            "    // LegacyRedrawable is deprecated but EraseHandler still relies on it; suppress the warning at\n"
            "    // this specific, known usage rather than change EraseHandler's behavior.\n"
            + PRAGMA_PUSH
            + "    EraseHandler(UndoRedoHandler* undo, Document* doc, const PageRef& page, ToolHandler* handler,\n"
            "                 LegacyRedrawable* view);\n"
            + PRAGMA_POP
            + "    virtual ~EraseHandler();",
        label="EraseHandler.h: constructeur",
    )
    ok &= apply_edit(
        f,
        old="private:\n    PageRef page;\n    ToolHandler* handler;\n    LegacyRedrawable* view;\n    Document* doc;",
        new="private:\n    PageRef page;\n    ToolHandler* handler;\n"
            + PRAGMA_PUSH
            + "    LegacyRedrawable* view;\n"
            + PRAGMA_POP
            + "    Document* doc;",
        label="EraseHandler.h: membre view",
    )

    # ================= EraseHandler.cpp : LegacyRedrawable deprecated =================
    f = Path("src/core/control/tools/EraseHandler.cpp")
    ok &= apply_edit(
        f,
        old="EraseHandler::EraseHandler(UndoRedoHandler* undo, Document* doc, const PageRef& page, ToolHandler* handler,\n"
            "                           LegacyRedrawable* view):\n"
            "        page(page),\n"
            "        handler(handler),\n"
            "        view(view),\n"
            "        doc(doc),\n"
            "        undo(undo),\n"
            "        eraseDeleteUndoAction(nullptr),\n"
            "        eraseUndoAction(nullptr),\n"
            "        halfEraserSize(0) {}",
        new=PRAGMA_PUSH
            + "EraseHandler::EraseHandler(UndoRedoHandler* undo, Document* doc, const PageRef& page, ToolHandler* handler,\n"
            "                           LegacyRedrawable* view):\n"
            "        page(page),\n"
            "        handler(handler),\n"
            "        view(view),\n"
            "        doc(doc),\n"
            "        undo(undo),\n"
            "        eraseDeleteUndoAction(nullptr),\n"
            "        eraseUndoAction(nullptr),\n"
            "        halfEraserSize(0) {}\n"
            + PRAGMA_POP,
        label="EraseHandler.cpp: définition du constructeur",
    )

    # ================= Control.cpp : Image::setImage deprecated =================
    f = Path("src/core/control/Control.cpp")
    ok &= apply_edit(
        f,
        old="    image->setImage(pixbuf.get());",
        new="    // Image::setImage(GdkPixbuf*) is deprecated in favor of the std::string_view overload, but that\n"
            "    // overload expects pre-encoded image bytes; reimplementing the GdkPixbuf->bytes encoding here\n"
            "    // risks producing different output than the existing (tested) deprecated implementation.\n"
            "    // Suppress the warning at this specific, known usage instead of risking a behavior change.\n"
            + PRAGMA_PUSH
            + "    image->setImage(pixbuf.get());\n"
            + PRAGMA_POP,
        label="Control.cpp: Image::setImage",
    )

    # ================= Document.cpp : wstring_convert deprecated =================
    f = Path("src/core/model/Document.cpp")
    ok &= apply_edit(
        f,
        old="    std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;\n"
            "    auto format = converter.from_bytes(char_cast(format_str).data());",
        new="    // std::wstring_convert is deprecated since C++17; the project already has a \"Todo (cpp20): use\n"
            "    // <format>\" marker here for a proper future rewrite. Suppress the warning at this specific,\n"
            "    // known usage rather than reimplement the UTF-8<->wide conversion now (risk of subtly changing\n"
            "    // filename encoding behavior on some platforms).\n"
            + PRAGMA_PUSH
            + "    std::wstring_convert<std::codecvt_utf8<wchar_t>> converter;\n"
            "    auto format = converter.from_bytes(char_cast(format_str).data());\n"
            + PRAGMA_POP,
        label="Document.cpp: wstring_convert",
    )

    # ================= luapi_application.h =================
    f = Path("src/core/plugin/luapi_application.h")

    ok &= apply_edit(
        f,
        old="    Plugin* plugin = Plugin::getPluginFromLua(L);\n\n"
            "    int result = XojMsgBox::askPluginQuestion(plugin->getName(), msg, buttons);\n"
            "    lua_pushinteger(L, result);\n"
            "    return 1;\n"
            "}",
        new="    Plugin* plugin = Plugin::getPluginFromLua(L);\n\n"
            "    // askPluginQuestion is the only API currently available to plugins for this; suppress the\n"
            "    // warning at this specific, known usage rather than change the plugin-facing behavior.\n"
            + PRAGMA_PUSH
            + "    int result = XojMsgBox::askPluginQuestion(plugin->getName(), msg, buttons);\n"
            + PRAGMA_POP
            + "    lua_pushinteger(L, result);\n"
            "    return 1;\n"
            "}",
        label="luapi_application.h: askPluginQuestion",
    )

    ok &= apply_edit(
        f,
        old="            return g_variant_new_int32(lua_tointeger(L, idx));",
        new="            return g_variant_new_int32(static_cast<gint32>(lua_tointeger(L, idx)));",
        label="luapi_application.h: lua_tointeger -> gint32",
    )

    ok &= apply_edit(
        f,
        old="            return g_variant_new_uint32(as_unsigned(lua_tointeger(L, idx)));",
        new="            return g_variant_new_uint32(static_cast<guint32>(as_unsigned(lua_tointeger(L, idx))));",
        label="luapi_application.h: as_unsigned -> guint32",
    )

    ok &= apply_edit(
        f,
        old="    size_t tab = control->getSidebar()->getSelectedTab();",
        new="    // getSelectedTab() is the only API currently available to plugins for this; suppress the\n"
            "    // warning at this specific, known usage rather than change the plugin-facing behavior.\n"
            + PRAGMA_PUSH
            + "    size_t tab = control->getSidebar()->getSelectedTab();\n"
            + PRAGMA_POP,
        label="luapi_application.h: getSelectedTab (sidebarAction)",
    )

    ok &= apply_edit(
        f,
        old="    Sidebar* sidebar = plugin->getControl()->getSidebar();\n"
            "    lua_pushinteger(L, as_signed(sidebar->getSelectedTab()) + 1);\n"
            "    return 1;",
        new="    Sidebar* sidebar = plugin->getControl()->getSidebar();\n"
            + PRAGMA_PUSH
            + "    lua_pushinteger(L, as_signed(sidebar->getSelectedTab()) + 1);\n"
            + PRAGMA_POP
            + "    return 1;",
        label="luapi_application.h: getSelectedTab (getSidebarPageNo)",
    )

    ok &= apply_edit(
        f,
        old="    if (as_unsigned(page) > sidebar->getNumberOfTabs()) {\n"
            "        lua_pushnil(L);\n"
            '        lua_pushfstring(L, "Invalid pageNo (%d >= %d) provided!", page, sidebar->getNumberOfTabs());\n'
            "        return 2;\n"
            "    }",
        new=PRAGMA_PUSH
            + "    if (as_unsigned(page) > sidebar->getNumberOfTabs()) {\n"
            "        lua_pushnil(L);\n"
            '        lua_pushfstring(L, "Invalid pageNo (%d >= %d) provided!", page, sidebar->getNumberOfTabs());\n'
            "        return 2;\n"
            "    }\n"
            + PRAGMA_POP,
        label="luapi_application.h: getNumberOfTabs",
    )

    print()
    if ok:
        print("Toutes les modifications ont été appliquées avec succès.")
        sys.exit(0)
    else:
        print("Au moins une modification a échoué. Vérifiez le [ECHEC] ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    main()
