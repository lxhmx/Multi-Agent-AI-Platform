"""
Property-based tests for chat history feature.

Uses Hypothesis library for property-based testing.
Each test runs a minimum of 100 iterations.
"""
import pytest
from hypothesis import given, settings, strategies as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.repositories import session_repo, message_repo


# Custom strategies for generating test data
message_content_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'S', 'Z')),
    min_size=1,
    max_size=500
).filter(lambda x: x.strip())  # Ensure non-empty after strip

role_strategy = st.sampled_from(['user', 'assistant'])


class TestMessagePersistenceRoundTrip:
    """
    **Feature: chat-history, Property 1: Message persistence round-trip**
    
    *For any* message (user or assistant) added to a session, retrieving that 
    session's messages SHALL return the exact same content that was saved.
    
    **Validates: Requirements 1.1, 1.2, 3.1**
    """
    
    @settings(max_examples=100)
    @given(
        content=message_content_strategy,
        role=role_strategy
    )
    def test_message_round_trip(self, test_user, cleanup_sessions, content, role):
        """
        Property: For any message content and role, saving and retrieving
        should return the exact same content.
        """
        # Create a session for the test
        session = session_repo.create_session(test_user, "Test Session")
        cleanup_sessions.append(session['id'])
        
        # Create message
        created_message = message_repo.create_message(
            session_id=session['id'],
            role=role,
            content=content
        )
        
        # Retrieve messages
        messages = message_repo.get_messages_by_session(session['id'])
        
        # Find our message
        found_message = next(
            (m for m in messages if m['id'] == created_message['id']),
            None
        )
        
        # Property: content should be exactly preserved
        assert found_message is not None, "Message should be retrievable"
        assert found_message['content'] == content, \
            f"Content mismatch: expected '{content}', got '{found_message['content']}'"
        assert found_message['role'] == role, \
            f"Role mismatch: expected '{role}', got '{found_message['role']}'"


class TestUniqueSessionIdGeneration:
    """
    **Feature: chat-history, Property 5: Unique session ID generation**
    
    *For any* number of session creation requests, each created session SHALL 
    have a unique identifier that does not collide with any existing session ID.
    
    **Validates: Requirements 4.1**
    """
    
    @settings(max_examples=100)
    @given(
        num_sessions=st.integers(min_value=2, max_value=10),
        titles=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
            min_size=2,
            max_size=10
        )
    )
    def test_unique_session_ids(self, test_user, cleanup_sessions, num_sessions, titles):
        """
        Property: Creating multiple sessions should always produce unique IDs.
        """
        # Limit to available titles
        actual_count = min(num_sessions, len(titles))
        
        created_ids = set()
        
        for i in range(actual_count):
            session = session_repo.create_session(test_user, titles[i])
            cleanup_sessions.append(session['id'])
            
            # Property: each new ID should be unique
            assert session['id'] not in created_ids, \
                f"Duplicate session ID detected: {session['id']}"
            
            created_ids.add(session['id'])
        
        # Verify all IDs are unique
        assert len(created_ids) == actual_count, \
            f"Expected {actual_count} unique IDs, got {len(created_ids)}"
