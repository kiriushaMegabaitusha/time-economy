"""Skills screen for Time Economy TUI."""

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Button, Label
from textual.reactive import reactive

from app.services import get_session, get_skills_directory, get_skill_matches


class SkillsScreen(Screen):
    """Skills directory screen - consistent Universal Design layout."""

    skills_data = reactive({"skills": [], "wants": []})
    matches_data = reactive([])

    def compose(self) -> None:
        with Container(id="skills-container", classes="screen-container"):
            yield Static("TIME ECONOMY - SKILLS DIRECTORY", id="header")
            yield Static("D:Dash M:Members T:Trans N:Needs G:Govern S:Skills | R:Refresh Q:Quit", id="nav-bar")

            with Horizontal(id="skills-content", classes="content-area split-view"):
                with Container(id="skills-offered-container", classes="split-left"):
                    yield Static("SKILLS OFFERED", classes="panel-title")
                    yield DataTable(id="skills-table")

                with Container(id="skills-wanted-container", classes="split-right"):
                    yield Static("SKILLS WANTED", classes="panel-title")
                    yield DataTable(id="wants-table")

            with Container(id="matches-container", classes="content-area"):
                yield Static("SKILL MATCHES - Who needs what someone offers", classes="panel-title")
                yield DataTable(id="matches-table")

            with Horizontal(id="skills-actions", classes="action-bar"):
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Skills directory - view matches to find collaboration opportunities", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_focus_after_refresh("#skills-table")

    def set_focus_after_refresh(self, table_id: str) -> None:
        """Focus the DataTable after data is loaded."""
        def do_focus():
            try:
                table = self.query_one(table_id, DataTable)
                table.focus()
            except Exception:
                pass
        self.call_later(do_focus)

    def refresh_data(self) -> None:
        db = get_session()
        try:
            directory = get_skills_directory(db)
            self.skills_data = {
                "skills": directory["skills"],
                "wants": directory["wants"]
            }
            self.matches_data = get_skill_matches(db)
        finally:
            db.close()

    def watch_skills_data(self, data) -> None:
        skills_table = self.query_one("#skills-table", DataTable)
        skills_table.clear(columns=True)
        skills_table.add_columns("Skill", "Category", "Member")
        for skill in data["skills"]:
            skills_table.add_row(
                f"[*] {skill.name}",
                skill.category or "-",
                skill.member_name or "?"
            )

        wants_table = self.query_one("#wants-table", DataTable)
        wants_table.clear(columns=True)
        wants_table.add_columns("Want", "Member")
        for want in data["wants"]:
            wants_table.add_row(
                f"[?] {want.name}",
                want.member_name or "?"
            )

        skill_count = len(data["skills"])
        want_count = len(data["wants"])
        self.query_one("#footer", Static).update(
            f"Skills: {skill_count} offered | Wants: {want_count} wanted | [R]efresh"
        )

    def watch_matches_data(self, data) -> None:
        matches_table = self.query_one("#matches-table", DataTable)
        matches_table.clear(columns=True)
        matches_table.add_columns("Who Wants", "Skill Needed", "Who Offers", "Skill")
        for match in data:
            matches_table.add_row(
                match["want_member"],
                f"[?]{match['want_name']}",
                match["skill_member"],
                f"[*]{match['skill_name']}"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh":
            self.refresh_data()