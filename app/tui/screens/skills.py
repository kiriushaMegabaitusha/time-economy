"""Skills screen for Time Economy TUI."""

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, DataTable, Button
from textual.reactive import reactive

from app.services import get_session, get_skills_directory, get_skill_matches


class SkillsScreen(Screen):
    """Skills directory screen."""

    skills_data = reactive({"skills": [], "wants": []})
    matches_data = reactive([])

    def compose(self) -> None:
        with Container(id="skills-container"):
            yield Static("TIME ECONOMY - SKILLS DIRECTORY", id="header")
            yield Static("Keys: [s]kills [d]ashboard [m]embers [t]ransactions [n]eeds [g]overnance  [r]efresh  [q]uit", id="nav-bar")

            with Horizontal(id="skills-content"):
                with Container(id="skills-offered-container"):
                    yield Static("SKILLS OFFERED", classes="panel-title")
                    yield DataTable(id="skills-table")

                with Container(id="skills-wanted-container"):
                    yield Static("SKILLS WANTED", classes="panel-title")
                    yield DataTable(id="wants-table")

            with Container(id="matches-container"):
                yield Static("MATCHES", classes="panel-title")
                yield DataTable(id="matches-table")

            with Horizontal(id="skills-actions"):
                yield Button("Refresh", variant="primary", id="btn-refresh")

            yield Static("Ready", id="footer")

    def on_mount(self) -> None:
        self.refresh_data()

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
                skill.name,
                skill.category or "",
                skill.member_name or "?"
            )

        wants_table = self.query_one("#wants-table", DataTable)
        wants_table.clear(columns=True)
        wants_table.add_columns("Want", "Member")
        for want in data["wants"]:
            wants_table.add_row(
                want.name,
                want.member_name or "?"
            )

    def watch_matches_data(self, data) -> None:
        matches_table = self.query_one("#matches-table", DataTable)
        matches_table.clear(columns=True)
        matches_table.add_columns("Who Needs", "What", "Who Offers", "What")
        for match in data:
            matches_table.add_row(
                match["want_member"],
                match["want_name"],
                match["skill_member"],
                match["skill_name"]
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh":
            self.refresh_data()
