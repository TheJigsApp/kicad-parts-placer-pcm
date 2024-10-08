import logging
import os
import sys
import csv
from pathlib import Path
import wx
import wx.aui
from wx.lib import buttons
import pcbnew
import dataclasses

path_ = Path(__file__).parent.absolute()
sys.path.append(str(path_))

from dataframe_lite_ import DataFrame
import kicad_parts_placer_
import _version

_log = logging.getLogger("kicad_partsplacer-pcm")
_log.setLevel(logging.DEBUG)

_board = None
_frame_size = (800, 600)
_frame_size_min = (500, 300)


def read_csv(fname: str, **kwargs):
    """
    Basic CSV reading to dataframe
    """
    with open(fname, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, **kwargs)
        return DataFrame(list(reader))


def set_board(board):
    """
    Sets the board global.
    """
    global _board
    _board = board


def get_board():
    """
    Use instead of pcbnew.GetBoard to allow
    command line use.
    """
    return _board


class Settings:
    """
    All the options that can be passed
    """

    def __init__(self):
        self.use_aux_origin: bool = False
        self.group_name = "parts placer"
        self.mirror = False
        self.group = False


@dataclasses.dataclass
class Meta:
    """
    Information about package
    """

    toolname: str = "kicadpartsplacer"
    title: str = "Parts Placer"
    body: str = (
        "Flip, mirror, move, rotate, and move components based off inputs from a spreadsheet. \
Enforce a form-factor, keep mechanical placements under version control, and allow \
updating of a templated design. Easily enforce grids or maintain test point patterns."
    )
    about_text: str = "Declaratively place components using a spreadsheet"
    short_description: str = "Parts Placer"
    frame_title: str = "Parts Placer"
    website: str = "https://www.thejigsapp.com"
    gitlink: str = "https://github.com/snhobbs/kicad-parts-placer-pcm"
    version: str = _version.__version__
    category: str = "Write PCB"
    icon_dir: Path = Path(__file__).parent
    icon_file_path: Path = icon_dir / "icon-24x24.png"


def setattr_keywords(obj, name, value):
    return setattr(obj, name, value)


class MyPanel(wx.Panel):
    """
    Primary panel
    """

    def __init__(self, parent):
        _log.debug("MyPanel.__init__")
        super().__init__(parent)
        self.settings = Settings()

        # Get current working directory
        dir_ = Path(os.getcwd())
        if pcbnew.GetBoard():
            set_board(pcbnew.GetBoard())

        if get_board():
            wd = Path(get_board().GetFileName()).absolute()
            if wd.exists():
                dir_ = wd.parent
        default_file_path = dir_ / f"{Meta.toolname}-report.csv"
        default_board_file_path = dir_ / f"{Meta.toolname}.kicad_pcb"

        file_label = wx.StaticText(self, label="File Input:")
        self.file_selector = wx.FilePickerCtrl(
            self,
            style=wx.FLP_SAVE | wx.FLP_USE_TEXTCTRL,
            wildcard="CSV files (*.csv)|*.csv",
            path=default_file_path.as_posix(),
        )
        self.file_selector.SetPath(default_file_path.as_posix())

        file_output_label = wx.StaticText(self, label="File Backup:")
        self.file_output_selector = wx.FilePickerCtrl(
            self,
            style=wx.FLP_SAVE | wx.FLP_USE_TEXTCTRL,
            wildcard="KiCAD PCB (*.kicad_pcb)|*.kicad_pcb",
            path=default_board_file_path.as_posix(),
        )
        self.file_output_selector.SetPath(default_board_file_path.as_posix())

        # Lorem Ipsum text
        lorem_text = wx.StaticText(self, label=Meta.body)

        # Buttons
        self.submit_button = buttons.GenButton(self, label="Submit")
        self.cancel_button = buttons.GenButton(self, label="Cancel")
        self.submit_button.SetBackgroundColour(wx.Colour(100, 225, 100))
        self.cancel_button.SetBackgroundColour(wx.Colour(225, 100, 100))
        self.submit_button.Bind(wx.EVT_BUTTON, self.on_submit)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)

        # Horizontal box sizer for buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.submit_button, 0, wx.ALL | wx.EXPAND, 5)
        button_sizer.Add(self.cancel_button, 0, wx.ALL, 5)

        # Origin selectiondd
        self.use_aux_origin_cb = wx.CheckBox(self, label="Use drill/place file origin")
        self.use_aux_origin_cb.SetValue(True)
        self.settings.use_aux_origin = self.use_aux_origin_cb.GetValue()

        # Group
        self.group_parts_cb = wx.CheckBox(self, label="Group Parts")
        self.group_parts_cb.SetValue(True)
        self.settings.group = self.group_parts_cb.GetValue()

        self.Bind(wx.EVT_CHECKBOX, self.on_checkbox_toggle)

        # Sizer for layout
        # sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.use_aux_origin_cb, 0, wx.ALL, 10)
        sizer.Add(self.group_parts_cb, 0, wx.ALL, 10)

        sizer.Add(file_label, 0, wx.ALL, 5)
        sizer.Add(self.file_selector, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(file_output_label, 0, wx.ALL, 5)
        sizer.Add(self.file_output_selector, 0, wx.EXPAND | wx.ALL, 5)

        sizer.Add(lorem_text, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(sizer)

    def on_checkbox_toggle(self, _):
        self.settings.use_aux_origin = self.use_aux_origin_cb.GetValue()
        self.settings.group = self.group_parts_cb.GetValue()
        _log.debug(self.settings.use_aux_origin)
        _log.debug(self.settings.group)

    def on_submit(self, _):
        file_path = Path(self.file_selector.GetPath())
        output_file_path = Path(self.file_output_selector.GetPath())

        if not file_path or not output_file_path:
            wx.MessageBox(
                "Please select an input and output file.",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return

        print("Submitting...")
        print("File Path:", file_path)

        board = get_board()
        if not board:
            wx.MessageBox(
                "No board found",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return

        origin = (0, 0)
        if self.settings.use_aux_origin:
            ds = board.GetDesignSettings()
            origin = pcbnew.ToMM(ds.GetAuxOrigin())

        _log.debug("Save Board")
        pcbnew.SaveBoard(str(output_file_path), board)

        if not file_path.exists():
            wx.MessageBox(
                "Spreadsheet not found",
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return

        components_df = read_csv(file_path)
        components_df.columns = kicad_parts_placer_.translate_header(
            components_df.columns
        )
        components_df = kicad_parts_placer_.setup_dataframe(components_df)
        for field in ["x", "y", "rotation"]:
            if field not in components_df.columns:
                continue
            components_df[field] = [float(pt) for pt in components_df[field]]

        valid, errors = kicad_parts_placer_.check_input_valid(components_df)
        if len(errors):
            msg = "%s\n%s" % ("\n".join(errors), ", ".join(components_df.columns))
            wx.MessageBox(
                msg,
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return

        missing_refs = kicad_parts_placer_.get_missing_references(board, components_df)
        if len(missing_refs):
            msg = "References not found on board: %s" % (", ".join(missing_refs))
            wx.MessageBox(
                msg,
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
            return

        board = kicad_parts_placer_.place_parts(
            board, components_df=components_df, origin=origin
        )

        group_name = self.settings.group_name
        if self.settings.group:
            _log.debug("GROUPING PARTS")
            board = kicad_parts_placer_.group_parts(
                board, components_df, group_name=group_name
            )

        wx.MessageBox(
            f"Moved: {len(components_df)}\nBackup PCB: {str(output_file_path)}",
            "Success",
            wx.OK,
        )

        self.GetTopLevelParent().EndModal(wx.ID_OK)
        # self.GetTopLevelParent().EndModal(wx.ID_CANCEL)
        return

    def on_cancel(self, _):
        print("Canceling...")
        self.GetTopLevelParent().EndModal(wx.ID_CANCEL)


class AboutPanel(wx.Panel):
    """
    About panel tab
    """

    def __init__(self, parent):
        super().__init__(parent)
        font = wx.Font(
            12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        bold = wx.Font(
            10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD
        )

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Static text for about information
        version_text = wx.StaticText(self, label=f"Version: {Meta.version}")
        version_text.SetFont(bold)
        sizer.Add(version_text, 1, wx.EXPAND | wx.ALL, 5)

        message_text = wx.StaticText(self, label=Meta.about_text)
        message_text.SetFont(font)
        sizer.Add(message_text, 1, wx.EXPAND | wx.ALL, 5)

        body_text = wx.StaticText(self, label=Meta.body)
        body_text.SetFont(font)
        sizer.Add(body_text, 5, wx.EXPAND | wx.ALL, 5)

        input_header_text = wx.StaticText(self, label="Input Format:")
        input_header_text.SetFont(bold)
        sizer.Add(input_header_text, 1, wx.EXPAND | wx.ALL, 5)

        input_header_body_text = wx.StaticText(
            self, label="Note: White space and character case ignored"
        )
        input_header_body_text.SetFont(font)
        sizer.Add(input_header_body_text, 1, wx.EXPAND | wx.ALL, 5)

        list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)
        list_ctrl.InsertColumn(0, "Field", width=150)
        list_ctrl.InsertColumn(1, "Alias", width=500)
        list_ctrl.InsertColumn(2, "Required", width=100)

        for key, value in kicad_parts_placer_._header_pseudonyms.items():
            index = list_ctrl.InsertItem(list_ctrl.GetItemCount(), key)
            list_ctrl.SetItem(index, 1, ", ".join(value))
            list_ctrl.SetItem(
                index, 2, str(key in kicad_parts_placer_._required_columns)
            )
        sizer.Add(list_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        from wx.lib.agw.hyperlink import HyperLinkCtrl

        link_sizer = wx.BoxSizer(wx.HORIZONTAL)

        pre_link_text = wx.StaticText(self, label="Brought to you by TheJigsApp: ")
        pre_link_text.SetFont(font)
        link_sizer.Add(pre_link_text, 0, wx.EXPAND, 0)

        link = HyperLinkCtrl(self, wx.ID_ANY, f"{Meta.website}", URL=Meta.website)
        link.SetFont(font)
        link.SetColours(wx.BLUE, wx.BLUE, wx.BLUE)
        link_sizer.Add(link, 0, wx.EXPAND, 0)

        sizer.Add(link_sizer, 1, wx.EXPAND | wx.ALL, 5)

        gh_link_sizer = wx.BoxSizer(wx.HORIZONTAL)

        gh_pre_link_text = wx.StaticText(self, label="Git Repo: ")
        gh_pre_link_text.SetFont(font)
        gh_link_sizer.Add(gh_pre_link_text, 0, wx.EXPAND, 0)

        gh_link = HyperLinkCtrl(self, wx.ID_ANY, f"{Meta.gitlink}", URL=Meta.gitlink)
        gh_link.SetFont(font)
        gh_link.SetColours(wx.BLUE, wx.BLUE, wx.BLUE)
        gh_link_sizer.Add(gh_link, 0, wx.EXPAND, 0)

        sizer.Add(gh_link_sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


class MyDialog(wx.Dialog):
    """
    Top level GUI view
    """

    def __init__(self, parent, title):
        super().__init__(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )

        # Sizer for layout
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        # Create a notebook with two tabs
        notebook = wx.Notebook(self)
        tab_panel = MyPanel(notebook)
        about_panel = AboutPanel(notebook)

        notebook.AddPage(tab_panel, "Main")
        notebook.AddPage(about_panel, "About")

        sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)
        self.SetMinSize(_frame_size_min)
        self.SetSize(_frame_size)

    def on_close(self, event):
        self.EndModal(wx.ID_CANCEL)
        event.Skip()

    def on_maximize(self, _):
        self.fit_to_screen()

    def on_size(self, _):
        if self.IsMaximized():
            self.fit_to_screen()

    def fit_to_screen(self):
        screen_width, screen_height = wx.DisplaySize()
        self.SetSize(wx.Size(screen_width, screen_height))


def get_gui_frame(name: str = "PcbFrame"):
    pcb_frame = None

    try:
        pcb_frame = [x for x in wx.GetTopLevelWindows() if x.GetName() == name][0]
    except IndexError:
        pass
    return pcb_frame


class Plugin(pcbnew.ActionPlugin):
    def __init__(self):
        super().__init__()

        _log.debug("Loading kicad_partsplacer")

        self.logger = _log
        self.config_file = None

        self.name = Meta.title
        self.category = Meta.category
        self.pcbnew_icon_support = hasattr(self, "show_toolbar_button")
        self.show_toolbar_button = True
        self.description = Meta.body

        # assert icon_file_path.exists()
        self.icon_file_name = str(Meta.icon_file_path)

    def defaults(self):
        pass

    def Run(self):
        dlg = MyDialog(get_gui_frame(name="PcbFrame"), title=Meta.title)
        try:
            dlg.ShowModal()

        except Exception as e:
            _log.error(e)
            raise
        finally:
            _log.debug("Destroy Dialog")
            dlg.Destroy()


if __name__ == "__main__":
    logging.basicConfig()
    _log.setLevel(logging.DEBUG)

    if len(sys.argv) > 1:
        set_board(pcbnew.LoadBoard(sys.argv[1]))
    app = wx.App()
    p = Plugin()
    p.Run()
