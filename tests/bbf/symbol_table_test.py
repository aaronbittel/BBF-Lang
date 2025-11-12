from bbf.symbol_table import SymbolTable, VarType


def test_define_and_lookup_local():
    table = SymbolTable()
    offset = table.define("x", VarType.Int)
    varinfo = table.lookup("x")

    assert varinfo is not None
    assert varinfo.offset == offset
    assert varinfo.ttype == VarType.Int


def test_lookup_nonexistent_variable():
    table = SymbolTable()
    assert table.lookup("nonexistent") is None


def test_parent_scope_lookup():
    parent = SymbolTable()
    offset = parent.define("x", VarType.Int)

    child = SymbolTable(parent=parent)

    varinfo = child.lookup("x")
    assert varinfo is not None
    assert varinfo.ttype == VarType.Int
    assert offset == varinfo.offset


def test_child_scope_shadowing_parent():
    parent = SymbolTable()
    p_offset = parent.define("x", VarType.Int)

    child = SymbolTable(parent=parent)
    c_offset = child.define("x", VarType.String)

    varinfo = child.lookup("x")
    assert varinfo is not None
    assert varinfo.ttype == VarType.String
    assert varinfo.offset == c_offset

    varinfo_parent = parent.lookup("x")
    assert varinfo_parent is not None
    assert varinfo_parent.ttype == VarType.Int
    assert varinfo.offset == p_offset


def test_multiple_levels_of_parent_scopes():
    root = SymbolTable()
    root.define("a", VarType.Int)

    middle = SymbolTable(parent=root)
    middle.define("b", VarType.String)

    leaf = SymbolTable(parent=middle)
    leaf.define("c", VarType.Int)

    assert leaf.lookup("a").ttype == VarType.Int
    assert leaf.lookup("b").ttype == VarType.String
    assert leaf.lookup("c").ttype == VarType.Int

    assert leaf.lookup("nonexistent") is None
