import pytest
from unittest.mock import MagicMock
from pymongo.collection import Collection
from app.models.stages import Stages


@pytest.fixture
def mock_collection():
    """
    Fixture for a mocked MongoDB collection.
    """
    return MagicMock(spec=Collection)


@pytest.fixture
def sample_stage(mock_collection):
    """
    Fixture for a sample stage instance.
    """
    return Stages(
        stage_id="stage1",
        stage_name="Stage 1",
        description="Description for Stage 1",
        _id="test1",
        _description="Test description",
        text="Sample text",
        type="test_type",
        collection=mock_collection
    )


def test_to_dict(sample_stage):
    """
    Test the `to_dict` method of the Stages class.
    """
    stage_dict = sample_stage.to_dict()
    assert stage_dict["id"] == "stage1"
    assert stage_dict["name"] == "Stage 1"
    assert stage_dict["description"] == "Description for Stage 1"
    assert len(stage_dict["test_item"]) == 1
    assert stage_dict["test_item"][0]["_id"] == "test1"


def test_insert_stage(sample_stage, mock_collection):
    """
    Test the `insert_stage` method of the Stages class.
    """
    mock_collection.insert_one.return_value.inserted_id = "mock_id"

    inserted_id = sample_stage.insert_stage()

    mock_collection.insert_one.assert_called_once_with(sample_stage.to_dict())
    assert inserted_id == "mock_id"


def test_get_one(sample_stage, mock_collection):
    """
    Test the `get_one` method of the Stages class.
    """
    mock_stage = {"id": "stage1", "name": "Stage 1"}
    mock_collection.find_one.return_value = mock_stage

    stage = sample_stage.get_one("stage1")

    mock_collection.find_one.assert_called_once_with({"id": "stage1"})
    assert stage == mock_stage


def test_get_all(sample_stage, mock_collection):
    """
    Test the `get_all` method of the Stages class.
    """
    mock_stages = [{"id": "stage1"}, {"id": "stage2"}]
    mock_collection.find.return_value = mock_stages

    stages = sample_stage.get_all()

    mock_collection.find.assert_called_once()
    assert stages == mock_stages


def test_delete_one(sample_stage, mock_collection):
    """
    Test the `delete_one` method of the Stages class.
    """
    mock_collection.delete_one.return_value.deleted_count = 1

    deleted_count = sample_stage.delete_one("stage1")

    mock_collection.delete_one.assert_called_once_with({"id": "stage1"})
    assert deleted_count == 1


def test_update(sample_stage, mock_collection):
    """
    Test the `update` method of the Stages class.
    """
    mock_collection.update_one.return_value.modified_count = 1
    updates = {"name": "Updated Stage Name"}

    modified_count = sample_stage.update("stage1", updates)

    mock_collection.update_one.assert_called_once_with({"id": "stage1"}, {"$set": updates})
    assert modified_count == 1
