"""Tests for AWS Bedrock LLM Provider Adapter.

Phase 8.8: AWS Bedrock Provider, Grounded Synthesis & Streaming Tokens.
"""

import json
from unittest.mock import MagicMock
import pytest

from app.ai.context_builder import (
    INSUFFICIENT_INFORMATION_MESSAGE,
    GroundedContextChunk,
)
from app.ai.llm import (
    BaseLLMProvider,
    BedrockLLMProvider,
    get_llm_provider,
)


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def make_context_chunk(
    chunk_id: str = "CHK-001",
    doc_id: str = "DOCU-001",
    title: str = "Cardiology Note",
    content: str = "Patient prescribed Metoprolol 25mg daily for tachycardia.",
    page: int = 1,
) -> GroundedContextChunk:
    return GroundedContextChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        title=title,
        content=content,
        page_number=page,
        document_type="clinical_note",
        distance=0.08,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_bedrock_provider_factory():
    """Verify get_llm_provider returns BedrockLLMProvider instance."""
    provider = get_llm_provider("bedrock")
    assert isinstance(provider, BedrockLLMProvider)
    assert isinstance(provider, BaseLLMProvider)


def test_bedrock_generate_empty_context():
    """Empty context chunks must immediately return insufficient information."""
    provider = BedrockLLMProvider()
    response = provider.generate_grounded_response(
        query="What is the patient's blood pressure?",
        context_chunks=[],
    )
    assert response.insufficient_information is True
    assert response.answer == INSUFFICIENT_INFORMATION_MESSAGE
    assert len(response.citations) == 0


def test_bedrock_mocked_boto3_generation():
    """Test successful grounded response generation using mocked boto3 client."""
    mock_boto_client = MagicMock()
    mock_response_body = {
        "content": [
            {
                "type": "text",
                "text": "Based on the records, the patient was prescribed Metoprolol 25mg [CHUNK_ID: CHK-001].",
            }
        ]
    }
    mock_body_stream = MagicMock()
    mock_body_stream.read.return_value = json.dumps(mock_response_body).encode("utf-8")
    mock_boto_client.invoke_model.return_value = {"body": mock_body_stream}

    provider = BedrockLLMProvider(client=mock_boto_client)
    chunk = make_context_chunk()

    response = provider.generate_grounded_response(
        query="What medication was prescribed for tachycardia?",
        context_chunks=[chunk],
    )

    assert response.insufficient_information is False
    assert "metoprolol" in response.answer.lower()
    assert len(response.citations) >= 1
    assert response.citations[0].chunk_id == "CHK-001"
    assert response.citations[0].document_id == "DOCU-001"

    # Verify invoke_model was called with proper payload
    mock_boto_client.invoke_model.assert_called_once()
    call_args = mock_boto_client.invoke_model.call_args[1]
    assert call_args["modelId"] == provider.model_id
    payload = json.loads(call_args["body"])
    assert "<document_context>" in payload["system"]
    assert "CHK-001" in payload["system"]


def test_bedrock_multi_turn_history_forwarding():
    """Verify prior chat history is included in Bedrock messages payload."""
    mock_boto_client = MagicMock()
    mock_response_body = {
        "content": [{"type": "text", "text": "The target heart rate is under 80 bpm."}]
    }
    mock_body_stream = MagicMock()
    mock_body_stream.read.return_value = json.dumps(mock_response_body).encode("utf-8")
    mock_boto_client.invoke_model.return_value = {"body": mock_body_stream}

    provider = BedrockLLMProvider(client=mock_boto_client)
    chunk = make_context_chunk()
    chat_history = [
        {"role": "user", "content": "What medication was started?"},
        {"role": "assistant", "content": "Metoprolol 25mg was started."},
    ]

    provider.generate_grounded_response(
        query="What was the target heart rate?",
        context_chunks=[chunk],
        chat_history=chat_history,
    )

    call_args = mock_boto_client.invoke_model.call_args[1]
    payload = json.loads(call_args["body"])
    messages = payload["messages"]
    assert len(messages) == 3  # 2 history turns + 1 current query
    assert messages[0]["content"] == "What medication was started?"
    assert messages[1]["content"] == "Metoprolol 25mg was started."
    assert messages[2]["content"] == "What was the target heart rate?"


def test_bedrock_streaming_generator():
    """Verify Bedrock streaming adapter correctly processes event chunks."""
    mock_boto_client = MagicMock()
    delta1 = json.dumps({"type": "content_block_delta", "delta": {"text": "Based on "}}).encode("utf-8")
    delta2 = json.dumps({"type": "content_block_delta", "delta": {"text": "records, Metoprolol."}}).encode("utf-8")

    event_stream = [
        {"chunk": {"bytes": delta1}},
        {"chunk": {"bytes": delta2}},
    ]
    mock_boto_client.invoke_model_with_response_stream.return_value = {"body": event_stream}

    provider = BedrockLLMProvider(client=mock_boto_client)
    chunk = make_context_chunk()

    stream_gen = provider.generate_grounded_response_stream(
        query="Tell me about Metoprolol",
        context_chunks=[chunk],
    )
    tokens = list(stream_gen)
    assert tokens == ["Based on ", "records, Metoprolol."]
