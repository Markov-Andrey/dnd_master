"""Тесты квестов."""
import pytest
from core.quests import (
    Quest, QuestManager, QuestStatus, QuestType,
    QuestObjective, QuestReward, QUEST_TEMPLATES,
)


class TestQuestTemplates:
    def test_all_templates_exist(self):
        assert len(QUEST_TEMPLATES) == 8

    def test_template_fields(self):
        for qid, q in QUEST_TEMPLATES.items():
            assert q.id == qid
            assert q.name
            assert q.objectives
            assert q.rewards


class TestQuestManager:
    def setup_method(self):
        self.qm = QuestManager()
        self.qm.load_templates()

    def test_load_templates(self):
        assert len(self.qm.quests) == 8

    def test_get_available_quests(self):
        available = self.qm.get_available_quests(player_level=10)
        assert len(available) > 0

    def test_accept_quest(self):
        ok, msg = self.qm.accept_quest("goblin_hunt")
        assert ok is True
        assert len(self.qm.active_quests) == 1

    def test_accept_nonexistent_quest(self):
        ok, msg = self.qm.accept_quest("fake_quest")
        assert ok is False

    def test_progress_kill(self):
        self.qm.accept_quest("goblin_hunt")
        updates = self.qm.update_quest_progress("kill", "goblin", 3)
        assert len(updates) > 0

    def test_quest_completion(self):
        self.qm.accept_quest("wolf_pelts")
        self.qm.update_quest_progress("collect", "wolf_pelt", 3)
        q = self.qm.quests["wolf_pelts"]
        assert q.status == QuestStatus.COMPLETED

    def test_get_active_quests(self):
        self.qm.accept_quest("goblin_hunt")
        active = self.qm.get_active_quests()
        assert len(active) == 1

    def test_get_completed_quests(self):
        self.qm.accept_quest("wolf_pelts")
        self.qm.update_quest_progress("collect", "wolf_pelt", 3)
        completed = self.qm.get_completed_quests()
        assert len(completed) == 1


class TestQuestObjective:
    def test_progress(self):
        obj = QuestObjective(QuestType.KILL, "goblin", "Убить гоблинов", 0, 3)
        obj.progress(2)
        assert obj.current == 2
        assert obj.is_complete is False
        obj.progress(1)
        assert obj.current == 3
        assert obj.is_complete is True
