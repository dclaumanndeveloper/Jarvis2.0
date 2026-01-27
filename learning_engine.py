"""
Self-Learning Engine for Jarvis 2.0
Implements machine learning capabilities for pattern recognition,
user preference tracking, and adaptive behavior to create a truly
intelligent Iron Man's Jarvis-like experience.
"""

import asyncio
import aiofiles
import pickle
import json
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, Counter
import logging
import os
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import joblib

from conversation_manager import ConversationTurn, IntentType, ConversationContext
from services.path_manager import PathManager

# Configure logging
# logging.basicConfig(level=logging.INFO) # Controlled by main.py
logger = logging.getLogger(__name__)


class LearningType(Enum):
    """Types of learning patterns"""
    COMMAND_SEQUENCE = "command_sequence"
    USAGE_PATTERN = "usage_pattern"
    PREFERENCE = "preference"
    CONTEXT_PATTERN = "context_pattern"
    ERROR_CORRECTION = "error_correction"
    TEMPORAL_PATTERN = "temporal_pattern"

class PatternConfidence(Enum):
    """Confidence levels for learned patterns"""
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.9

@dataclass
class UserPattern:
    """Represents a learned user pattern"""
    pattern_id: str
    pattern_type: LearningType
    pattern_data: Dict[str, Any]
    frequency: int
    confidence: float
    first_observed: datetime
    last_used: datetime
    success_rate: float
    context_conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LearningSession:
    """Represents a learning session"""
    session_id: str
    start_time: datetime
    interactions: List[ConversationTurn]
    patterns_discovered: List[UserPattern]
    insights_generated: List[str]
    performance_metrics: Dict[str, float] = field(default_factory=dict)

class PatternRecognizer:
    """Advanced pattern recognition using machine learning"""
    
    def __init__(self, min_pattern_frequency: int = 3):
        self.min_pattern_frequency = min_pattern_frequency
        self.sequence_patterns = defaultdict(list)
        self.temporal_patterns = defaultdict(list)
        self.context_patterns = defaultdict(dict)
        
        # ML models
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words=None)
        self.clustering_model = None
        self.similarity_threshold = 0.7
        
        # Pattern storage
        self.learned_patterns = {}
        self.pattern_counter = Counter()
        
    def analyze_command_sequences(self, interactions: List[ConversationTurn]) -> List[UserPattern]:
        """Analyze command sequences to find patterns"""
        patterns = []
        
        # Extract command sequences
        command_sequences = self._extract_command_sequences(interactions)
        
        # Find frequent sequences
        sequence_counts = Counter(command_sequences)
        
        for sequence, count in sequence_counts.items():
            if count >= self.min_pattern_frequency and len(sequence) > 1:
                pattern = UserPattern(
                    pattern_id=f"seq_{hash(sequence)}",
                    pattern_type=LearningType.COMMAND_SEQUENCE,
                    pattern_data={
                        'sequence': sequence,
                        'commands': list(sequence),
                        'average_interval': self._calculate_average_interval(sequence, interactions)
                    },
                    frequency=count,
                    confidence=min(count / 10.0, 1.0),  # Normalize confidence
                    first_observed=self._find_first_occurrence(sequence, interactions),
                    last_used=self._find_last_occurrence(sequence, interactions),
                    success_rate=1.0  # Assume success for now
                )
                patterns.append(pattern)
        
        return patterns
    
    def analyze_temporal_patterns(self, interactions: List[ConversationTurn]) -> List[UserPattern]:
        """Analyze temporal usage patterns"""
        patterns = []
        
        # Group interactions by hour of day
        hourly_usage = defaultdict(list)
        for interaction in interactions:
            hour = interaction.timestamp.hour
            hourly_usage[hour].append(interaction)
        
        # Find peak usage hours
        usage_counts = {hour: len(interactions) for hour, interactions in hourly_usage.items()}
        
        # Identify patterns (e.g., high usage periods)
        max_usage = max(usage_counts.values()) if usage_counts else 0
        
        for hour, count in usage_counts.items():
            if count >= self.min_pattern_frequency and count / max_usage > 0.3:
                
                # Analyze what types of commands are common at this hour
                common_intents = Counter([turn.intent for turn in hourly_usage[hour]])
                
                pattern = UserPattern(
                    pattern_id=f"temporal_{hour}",
                    pattern_type=LearningType.TEMPORAL_PATTERN,
                    pattern_data={
                        'hour': hour,
                        'usage_count': count,
                        'common_intents': dict(common_intents.most_common(3)),
                        'typical_commands': self._extract_common_commands(hourly_usage[hour])
                    },
                    frequency=count,
                    confidence=count / max_usage,
                    first_observed=min(turn.timestamp for turn in hourly_usage[hour]),
                    last_used=max(turn.timestamp for turn in hourly_usage[hour]),
                    success_rate=1.0
                )
                patterns.append(pattern)
        
        return patterns
    
    def analyze_context_patterns(self, interactions: List[ConversationTurn]) -> List[UserPattern]:
        """Analyze contextual patterns in user behavior"""
        patterns = []
        
        # Group by intent types
        intent_groups = defaultdict(list)
        for interaction in interactions:
            intent_groups[interaction.intent].append(interaction)
        
        # Analyze patterns within each intent group
        for intent, turns in intent_groups.items():
            if len(turns) >= self.min_pattern_frequency:
                
                # Extract common entities
                all_entities = []
                for turn in turns:
                    all_entities.extend(turn.entities.keys())
                
                common_entities = Counter(all_entities).most_common(5)
                
                # Analyze response patterns
                response_patterns = self._analyze_response_patterns(turns)
                
                pattern = UserPattern(
                    pattern_id=f"context_{intent.value}",
                    pattern_type=LearningType.CONTEXT_PATTERN,
                    pattern_data={
                        'intent': intent.value,
                        'common_entities': dict(common_entities),
                        'response_patterns': response_patterns,
                        'average_confidence': np.mean([turn.confidence_score for turn in turns]),
                        'success_indicators': self._identify_success_indicators(turns)
                    },
                    frequency=len(turns),
                    confidence=min(len(turns) / 20.0, 1.0),
                    first_observed=min(turn.timestamp for turn in turns),
                    last_used=max(turn.timestamp for turn in turns),
                    success_rate=self._calculate_success_rate(turns)
                )
                patterns.append(pattern)
        
        return patterns
    
    def _extract_command_sequences(self, interactions: List[ConversationTurn]) -> List[Tuple[str, ...]]:
        """Extract command sequences from interactions"""
        sequences = []
        current_sequence = []
        last_time = None
        
        sequence_timeout = 300  # 5 minutes
        
        for interaction in sorted(interactions, key=lambda x: x.timestamp):
            if interaction.intent == IntentType.DIRECT_COMMAND:
                
                # Check if this continues the current sequence
                if (last_time and 
                    (interaction.timestamp - last_time).total_seconds() <= sequence_timeout):
                    current_sequence.append(interaction.user_input.lower().strip())
                else:
                    # Start new sequence
                    if len(current_sequence) > 1:
                        sequences.append(tuple(current_sequence))
                    current_sequence = [interaction.user_input.lower().strip()]
                
                last_time = interaction.timestamp
        
        # Add the last sequence
        if len(current_sequence) > 1:
            sequences.append(tuple(current_sequence))
        
        return sequences
    
    def _calculate_average_interval(self, sequence: Tuple[str, ...], 
                                   interactions: List[ConversationTurn]) -> float:
        """Calculate average time interval between commands in sequence"""
        intervals = []
        
        # Find occurrences of this sequence
        command_turns = [turn for turn in interactions if turn.intent == IntentType.DIRECT_COMMAND]
        
        for i in range(len(command_turns) - len(sequence) + 1):
            window = command_turns[i:i+len(sequence)]
            
            # Check if this window matches the sequence
            if tuple(turn.user_input.lower().strip() for turn in window) == sequence:
                # Calculate intervals
                for j in range(1, len(window)):
                    interval = (window[j].timestamp - window[j-1].timestamp).total_seconds()
                    intervals.append(interval)
        
        return np.mean(intervals) if intervals else 0.0
    
    def _find_first_occurrence(self, sequence: Tuple[str, ...], 
                              interactions: List[ConversationTurn]) -> datetime:
        """Find first occurrence of a sequence"""
        command_turns = [turn for turn in interactions if turn.intent == IntentType.DIRECT_COMMAND]
        
        for i in range(len(command_turns) - len(sequence) + 1):
            window = command_turns[i:i+len(sequence)]
            if tuple(turn.user_input.lower().strip() for turn in window) == sequence:
                return window[0].timestamp
        
        return datetime.now()
    
    def _find_last_occurrence(self, sequence: Tuple[str, ...], 
                             interactions: List[ConversationTurn]) -> datetime:
        """Find last occurrence of a sequence"""
        command_turns = [turn for turn in interactions if turn.intent == IntentType.DIRECT_COMMAND]
        
        for i in range(len(command_turns) - len(sequence), -1, -1):
            window = command_turns[i:i+len(sequence)]
            if tuple(turn.user_input.lower().strip() for turn in window) == sequence:
                return window[-1].timestamp
        
        return datetime.now()
    
    def _extract_common_commands(self, turns: List[ConversationTurn]) -> List[str]:
        """Extract most common commands from turns"""
        commands = [turn.user_input.lower().strip() for turn in turns 
                   if turn.intent == IntentType.DIRECT_COMMAND]
        
        command_counts = Counter(commands)
        return [cmd for cmd, count in command_counts.most_common(5)]
    
    def _analyze_response_patterns(self, turns: List[ConversationTurn]) -> Dict[str, Any]:
        """Analyze response patterns in turns"""
        responses = [turn.response for turn in turns if turn.response]
        
        if not responses:
            return {}
        
        # Simple response analysis
        response_lengths = [len(response.split()) for response in responses]
        response_sentiment = self._analyze_response_sentiment(responses)
        
        return {
            'average_length': np.mean(response_lengths),
            'sentiment_distribution': response_sentiment,
            'most_common_phrases': self._extract_common_phrases(responses)
        }
    
    def _analyze_response_sentiment(self, responses: List[str]) -> Dict[str, int]:
        """Simple sentiment analysis of responses"""
        positive_words = ['sucesso', 'perfeito', 'ótimo', 'executado', 'concluído']
        negative_words = ['erro', 'falha', 'problema', 'impossível', 'não consegui']
        
        sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for response in responses:
            response_lower = response.lower()
            if any(word in response_lower for word in positive_words):
                sentiment_counts['positive'] += 1
            elif any(word in response_lower for word in negative_words):
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
        
        return sentiment_counts
    
    def _extract_common_phrases(self, responses: List[str]) -> List[str]:
        """Extract common phrases from responses"""
        # Simple phrase extraction
        all_words = []
        for response in responses:
            all_words.extend(response.lower().split())
        
        word_counts = Counter(all_words)
        return [word for word, count in word_counts.most_common(10) if len(word) > 3]
    
    def _identify_success_indicators(self, turns: List[ConversationTurn]) -> List[str]:
        """Identify indicators of successful interactions"""
        success_indicators = []
        
        # Look for high confidence scores
        high_confidence_turns = [turn for turn in turns if turn.confidence_score > 0.8]
        if len(high_confidence_turns) / len(turns) > 0.7:
            success_indicators.append('high_confidence_recognition')
        
        # Look for quick response times
        quick_responses = [turn for turn in turns if turn.response_time < 2.0]
        if len(quick_responses) / len(turns) > 0.8:
            success_indicators.append('fast_response_time')
        
        return success_indicators
    
    def _calculate_success_rate(self, turns: List[ConversationTurn]) -> float:
        """Calculate success rate for a set of turns"""
        # Simple success rate based on satisfaction scores
        satisfied_turns = [turn for turn in turns 
                          if turn.satisfaction_score and turn.satisfaction_score > 0.7]
        
        if not turns:
            return 1.0
        
        return len(satisfied_turns) / len(turns)

class PreferenceTracker:
    """Tracks and learns user preferences over time"""
    
    def __init__(self):
        self.preferences = defaultdict(dict)
        self.preference_weights = defaultdict(float)
        self.preference_history = defaultdict(list)
        
    def learn_preferences(self, interactions: List[ConversationTurn]) -> Dict[str, Any]:
        """Learn user preferences from interactions"""
        preferences = {}
        
        # Response style preferences
        preferences['response_style'] = self._learn_response_style_preferences(interactions)
        
        # Command preferences
        preferences['command_patterns'] = self._learn_command_preferences(interactions)
        
        # Timing preferences
        preferences['timing'] = self._learn_timing_preferences(interactions)
        
        # Verbosity preferences
        preferences['verbosity'] = self._learn_verbosity_preferences(interactions)
        
        # Update internal preference tracking
        self._update_preference_weights(preferences)
        
        return preferences
    
    def _learn_response_style_preferences(self, interactions: List[ConversationTurn]) -> Dict[str, Any]:
        """Learn preferred response styles"""
        # Analyze successful interactions for style patterns
        successful_interactions = [turn for turn in interactions 
                                 if turn.satisfaction_score and turn.satisfaction_score > 0.7]
        
        if not successful_interactions:
            return {'style': 'professional', 'confidence': 0.5}
        
        # Analyze response characteristics
        formal_responses = 0
        casual_responses = 0
        
        for interaction in successful_interactions:
            response = interaction.response.lower()
            
            # Simple style detection
            if any(word in response for word in ['senhor', 'senhora', 'certamente', 'com prazer']):
                formal_responses += 1
            elif any(word in response for word in ['beleza', 'ok', 'legal', 'valeu']):
                casual_responses += 1
        
        if formal_responses > casual_responses:
            return {'style': 'formal', 'confidence': formal_responses / len(successful_interactions)}
        elif casual_responses > formal_responses:
            return {'style': 'casual', 'confidence': casual_responses / len(successful_interactions)}
        else:
            return {'style': 'professional', 'confidence': 0.7}
    
    def _learn_command_preferences(self, interactions: List[ConversationTurn]) -> Dict[str, Any]:
        """Learn command usage preferences"""
        command_interactions = [turn for turn in interactions if turn.intent == IntentType.DIRECT_COMMAND]
        
        # Most used commands
        commands = [turn.user_input.lower().strip() for turn in command_interactions]
        command_counts = Counter(commands)
        
        # Preferred command formats
        short_commands = [cmd for cmd in commands if len(cmd.split()) <= 2]
        long_commands = [cmd for cmd in commands if len(cmd.split()) > 2]
        
        return {
            'most_used': dict(command_counts.most_common(10)),
            'prefers_short_commands': len(short_commands) > len(long_commands),
            'average_command_length': np.mean([len(cmd.split()) for cmd in commands]) if commands else 0
        }
    
    def _learn_timing_preferences(self, interactions: List[ConversationTurn]) -> Dict[str, Any]:
        """Learn timing and scheduling preferences"""
        # Analyze usage patterns by time of day
        usage_by_hour = defaultdict(int)
        for interaction in interactions:
            hour = interaction.timestamp.hour
            usage_by_hour[hour] += 1
        
        # Find peak hours
        peak_hours = sorted(usage_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            'peak_hours': [hour for hour, count in peak_hours],
            'usage_distribution': dict(usage_by_hour),
            'prefers_morning': sum(usage_by_hour[h] for h in range(6, 12)) > sum(usage_by_hour[h] for h in range(18, 24)),
            'active_period': self._determine_active_period(usage_by_hour)
        }
    
    def _learn_verbosity_preferences(self, interactions: List[ConversationTurn]) -> Dict[str, Any]:
        """Learn verbosity preferences from user feedback"""
        # Look for indicators of verbosity preference
        responses = [turn.response for turn in interactions if turn.response]
        
        if not responses:
            return {'level': 'medium', 'confidence': 0.5}
        
        response_lengths = [len(response.split()) for response in responses]
        avg_length = np.mean(response_lengths)
        
        # Classify verbosity preference
        if avg_length < 5:
            verbosity_level = 'concise'
        elif avg_length > 15:
            verbosity_level = 'verbose'
        else:
            verbosity_level = 'medium'
        
        return {
            'level': verbosity_level,
            'average_response_length': avg_length,
            'confidence': min(len(responses) / 20.0, 1.0)
        }
    
    def _determine_active_period(self, usage_by_hour: Dict[int, int]) -> str:
        """Determine user's most active period"""
        morning = sum(usage_by_hour[h] for h in range(6, 12))
        afternoon = sum(usage_by_hour[h] for h in range(12, 18))
        evening = sum(usage_by_hour[h] for h in range(18, 24))
        night = sum(usage_by_hour[h] for h in range(0, 6))
        
        periods = {'morning': morning, 'afternoon': afternoon, 'evening': evening, 'night': night}
        return max(periods, key=periods.get)
    
    def _update_preference_weights(self, new_preferences: Dict[str, Any]):
        """Update preference weights based on new learning"""
        for category, prefs in new_preferences.items():
            if isinstance(prefs, dict) and 'confidence' in prefs:
                self.preference_weights[category] = prefs['confidence']
                self.preference_history[category].append({
                    'timestamp': datetime.now(),
                    'preferences': prefs
                })

class LearningModule:
    """
    Main learning module that orchestrates pattern recognition,
    preference tracking, and adaptive behavior for Jarvis 2.0
    """
    
    def __init__(self, data_dir: str = "learning_data"):
        if data_dir == "learning_data":
            self.data_dir = PathManager.get_learning_dir()
        else:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.pattern_recognizer = PatternRecognizer()
        self.preference_tracker = PreferenceTracker()
        
        # Learning state
        self.learned_patterns = {}
        self.user_preferences = {}
        self.learning_sessions = []
        
        # Configuration
        self.learning_enabled = True
        self.auto_learn_interval = 300  # 5 minutes
        self.pattern_update_threshold = 10  # interactions
        
        # Load existing learning data
        self._load_learning_data()
        
        # Background learning task
        self._learning_task: Optional[asyncio.Task] = None
    
    async def start_learning(self):
        """Start background learning process"""
        if not self.learning_enabled:
            logger.info("Learning is disabled")
            return
        
        logger.info("Starting learning engine...")
        self._learning_task = asyncio.create_task(self._continuous_learning_loop())
    
    async def stop_learning(self):
        """Stop background learning process"""
        logger.info("Stopping learning engine...")
        if self._learning_task:
            self._learning_task.cancel()
            try:
                await self._learning_task
            except asyncio.CancelledError:
                pass
        
        # Save learning data
        self._save_learning_data()
    
    async def learn_from_interaction(self, turn: ConversationTurn, context: ConversationContext):
        """Learn from a single interaction"""
        if not self.learning_enabled:
            return
        
        try:
            # Update interaction history
            await self._add_interaction_to_history(turn)
            
            # Immediate learning for important patterns
            if self._should_trigger_immediate_learning(turn):
                await self._process_immediate_learning([turn])
            
            logger.debug(f"Learned from interaction: {turn.user_input[:50]}...")
            
        except Exception as e:
            logger.error(f"Error in learning from interaction: {e}")
    
    async def generate_proactive_suggestions(self, context: ConversationContext) -> List[str]:
        """Generate proactive suggestions based on learned patterns"""
        suggestions = []
        
        try:
            current_time = datetime.now()
            current_hour = current_time.hour
            
            # Time-based suggestions
            temporal_suggestions = self._get_temporal_suggestions(current_hour)
            suggestions.extend(temporal_suggestions)
            
            # Sequence-based suggestions
            if context.last_command:
                sequence_suggestions = self._get_sequence_suggestions(context.last_command)
                suggestions.extend(sequence_suggestions)
            
            # Context-based suggestions
            context_suggestions = self._get_context_suggestions(context)
            suggestions.extend(context_suggestions)
            
            # Limit and rank suggestions
            suggestions = self._rank_suggestions(suggestions)[:3]
            
        except Exception as e:
            logger.error(f"Error generating proactive suggestions: {e}")
        
        return suggestions
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get current user preferences"""
        return self.user_preferences.copy()
    
    def get_learned_patterns(self) -> Dict[str, UserPattern]:
        """Get all learned patterns"""
        return self.learned_patterns.copy()
    
    def get_learning_insights(self) -> List[str]:
        """Get insights from learning analysis"""
        insights = []
        
        # Pattern insights
        if self.learned_patterns:
            most_frequent_pattern = max(self.learned_patterns.values(), key=lambda p: p.frequency)
            insights.append(f"Padrão mais frequente: {most_frequent_pattern.pattern_type.value}")
        
        # Preference insights
        if 'response_style' in self.user_preferences:
            style = self.user_preferences['response_style'].get('style', 'unknown')
            insights.append(f"Prefere respostas no estilo: {style}")
        
        return insights
    
    async def _continuous_learning_loop(self):
        """Continuous learning background process"""
        while self.learning_enabled:
            try:
                await asyncio.sleep(self.auto_learn_interval)
                
                # Get recent interactions
                recent_interactions = await self._get_recent_interactions()
                
                if len(recent_interactions) >= self.pattern_update_threshold:
                    await self._process_batch_learning(recent_interactions)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in continuous learning loop: {e}")
    
    async def _add_interaction_to_history(self, turn: ConversationTurn):
        """Add interaction to learning history"""
        # Simple file-based storage for now
        history_file = self.data_dir / "interaction_history.jsonl"
        
        try:
            async with aiofiles.open(history_file, 'a', encoding='utf-8') as f:
                interaction_data = {
                    'timestamp': turn.timestamp.isoformat(),
                    'user_input': turn.user_input,
                    'intent': turn.intent.value,
                    'entities': turn.entities,
                    'response': turn.response,
                    'confidence_score': turn.confidence_score,
                    'satisfaction_score': turn.satisfaction_score
                }
                await f.write(json.dumps(interaction_data, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Error saving interaction history: {e}")
    
    def _should_trigger_immediate_learning(self, turn: ConversationTurn) -> bool:
        """Determine if immediate learning should be triggered"""
        # Trigger for error corrections or high-confidence interactions
        return (turn.confidence_score > 0.9 or 
                turn.satisfaction_score and turn.satisfaction_score < 0.3)
    
    async def _process_immediate_learning(self, interactions: List[ConversationTurn]):
        """Process immediate learning from interactions"""
        try:
            # Quick pattern recognition
            new_patterns = self.pattern_recognizer.analyze_command_sequences(interactions)
            
            # Update learned patterns
            for pattern in new_patterns:
                self.learned_patterns[pattern.pattern_id] = pattern
            
            logger.info(f"Immediate learning processed {len(new_patterns)} patterns")
            
        except Exception as e:
            logger.error(f"Error in immediate learning: {e}")
    
    async def _process_batch_learning(self, interactions: List[ConversationTurn]):
        """Process batch learning from accumulated interactions"""
        try:
            logger.info(f"Processing batch learning with {len(interactions)} interactions")
            
            # Analyze patterns
            sequence_patterns = self.pattern_recognizer.analyze_command_sequences(interactions)
            temporal_patterns = self.pattern_recognizer.analyze_temporal_patterns(interactions)
            context_patterns = self.pattern_recognizer.analyze_context_patterns(interactions)
            
            # Update learned patterns
            all_patterns = sequence_patterns + temporal_patterns + context_patterns
            for pattern in all_patterns:
                self.learned_patterns[pattern.pattern_id] = pattern
            
            # Learn preferences
            new_preferences = self.preference_tracker.learn_preferences(interactions)
            self.user_preferences.update(new_preferences)
            
            # Create learning session
            session = LearningSession(
                session_id=f"batch_{int(time.time())}",
                start_time=datetime.now(),
                interactions=interactions,
                patterns_discovered=all_patterns,
                insights_generated=self.get_learning_insights()
            )
            self.learning_sessions.append(session)
            
            # Save updated data
            self._save_learning_data()
            
            logger.info(f"Batch learning complete: {len(all_patterns)} patterns, {len(new_preferences)} preferences")
            
        except Exception as e:
            logger.error(f"Error in batch learning: {e}")
    
    async def _get_recent_interactions(self) -> List[ConversationTurn]:
        """Get recent interactions from history (asynchronously)"""
        return await asyncio.to_thread(self._get_recent_interactions_sync)

    def _get_recent_interactions_sync(self) -> List[ConversationTurn]:
        """Get recent interactions from history"""
        interactions = []
        history_file = self.data_dir / "interaction_history.jsonl"
        
        if not history_file.exists():
            return interactions
        
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.auto_learn_interval)
            
            with open(history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(data['timestamp'])
                        
                        if timestamp > cutoff_time:
                            # Reconstruct ConversationTurn
                            turn = ConversationTurn(
                                id=f"hist_{int(timestamp.timestamp())}",
                                timestamp=timestamp,
                                user_input=data['user_input'],
                                recognized_text=data['user_input'],
                                confidence_score=data['confidence_score'],
                                intent=IntentType(data['intent']),
                                entities=data['entities'],
                                context={},
                                response=data['response'],
                                response_time=0.0,
                                satisfaction_score=data.get('satisfaction_score')
                            )
                            interactions.append(turn)
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        logger.warning(f"Error parsing interaction history line: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error reading interaction history: {e}")
        
        return interactions
    
    def _get_temporal_suggestions(self, current_hour: int) -> List[str]:
        """Get suggestions based on temporal patterns"""
        suggestions = []
        
        # Find patterns for this hour
        temporal_pattern_id = f"temporal_{current_hour}"
        if temporal_pattern_id in self.learned_patterns:
            pattern = self.learned_patterns[temporal_pattern_id]
            typical_commands = pattern.pattern_data.get('typical_commands', [])
            
            if typical_commands:
                suggestions.append(f"Você costuma executar '{typical_commands[0]}' neste horário.")
        
        return suggestions
    
    def _get_sequence_suggestions(self, last_command: str) -> List[str]:
        """Get suggestions based on command sequences"""
        suggestions = []
        
        # Look for patterns that start with the last command
        for pattern in self.learned_patterns.values():
            if (pattern.pattern_type == LearningType.COMMAND_SEQUENCE and 
                pattern.pattern_data.get('commands', [])):
                
                commands = pattern.pattern_data['commands']
                if commands[0].lower() == last_command.lower() and len(commands) > 1:
                    next_command = commands[1]
                    suggestions.append(f"Você geralmente executa '{next_command}' após '{last_command}'.")
        
        return suggestions
    
    def _get_context_suggestions(self, context: ConversationContext) -> List[str]:
        """Get suggestions based on current context"""
        suggestions = []
        
        # Context-based suggestions using learned preferences
        if 'command_patterns' in self.user_preferences:
            most_used = self.user_preferences['command_patterns'].get('most_used', {})
            
            if most_used:
                top_command = max(most_used, key=most_used.get)
                suggestions.append(f"Seu comando mais usado é '{top_command}'.")
        
        return suggestions
    
    def _rank_suggestions(self, suggestions: List[str]) -> List[str]:
        """Rank suggestions by relevance and confidence"""
        # Simple ranking - can be enhanced with ML
        return list(set(suggestions))  # Remove duplicates
    
    def _save_learning_data(self):
        """Save learning data to disk"""
        try:
            # Save patterns
            patterns_file = self.data_dir / "learned_patterns.pkl"
            with open(patterns_file, 'wb') as f:
                pickle.dump(self.learned_patterns, f)
            
            # Save preferences
            preferences_file = self.data_dir / "user_preferences.json"
            with open(preferences_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, ensure_ascii=False, indent=2)
            
            # Save learning sessions (last 10)
            sessions_file = self.data_dir / "learning_sessions.json"
            recent_sessions = self.learning_sessions[-10:] if len(self.learning_sessions) > 10 else self.learning_sessions
            
            sessions_data = []
            for session in recent_sessions:
                sessions_data.append({
                    'session_id': session.session_id,
                    'start_time': session.start_time.isoformat(),
                    'patterns_count': len(session.patterns_discovered),
                    'insights': session.insights_generated,
                    'performance_metrics': session.performance_metrics
                })
            
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)
            
            logger.info("Learning data saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving learning data: {e}")
    
    def _load_learning_data(self):
        """Load learning data from disk"""
        try:
            # Load patterns
            patterns_file = self.data_dir / "learned_patterns.pkl"
            if patterns_file.exists():
                with open(patterns_file, 'rb') as f:
                    self.learned_patterns = pickle.load(f)
                    logger.info(f"Loaded {len(self.learned_patterns)} learned patterns")
            
            # Load preferences
            preferences_file = self.data_dir / "user_preferences.json"
            if preferences_file.exists():
                with open(preferences_file, 'r', encoding='utf-8') as f:
                    self.user_preferences = json.load(f)
                    logger.info(f"Loaded user preferences: {list(self.user_preferences.keys())}")
            
        except Exception as e:
            logger.error(f"Error loading learning data: {e}")
            # Initialize with defaults
            self.learned_patterns = {}
            self.user_preferences = {}

# Example usage and testing
async def main():
    """Example usage of Learning Engine"""
    
    # Create learning module
    learning_module = LearningModule()
    
    # Start learning
    await learning_module.start_learning()
    
    # Simulate some interactions
    from conversation_manager import ConversationContext
    
    context = ConversationContext()
    
    # Create sample interactions
    sample_turns = [
        ConversationTurn(
            id="test1",
            timestamp=datetime.now(),
            user_input="abrir chrome",
            recognized_text="abrir chrome",
            confidence_score=0.9,
            intent=IntentType.DIRECT_COMMAND,
            entities={'applications': {'values': ['chrome']}},
            context={},
            response="Abrindo Chrome...",
            response_time=1.0,
            satisfaction_score=0.8
        ),
        ConversationTurn(
            id="test2",
            timestamp=datetime.now(),
            user_input="pesquisar python",
            recognized_text="pesquisar python",
            confidence_score=0.85,
            intent=IntentType.DIRECT_COMMAND,
            entities={'actions': {'values': ['pesquisar']}},
            context={},
            response="Pesquisando python...",
            response_time=1.2,
            satisfaction_score=0.9
        )
    ]
    
    # Learn from interactions
    for turn in sample_turns:
        await learning_module.learn_from_interaction(turn, context)
    
    # Generate suggestions
    suggestions = await learning_module.generate_proactive_suggestions(context)
    print(f"🧠 Proactive suggestions: {suggestions}")
    
    # Get insights
    insights = learning_module.get_learning_insights()
    print(f"💡 Learning insights: {insights}")
    
    # Stop learning
    await learning_module.stop_learning()
    
    print("Learning engine test completed!")

if __name__ == "__main__":
    asyncio.run(main())
