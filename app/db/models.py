from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProgressItemType(StrEnum):
    WORD = "word"
    VERB = "verb"
    CONJUGATION = "conjugation"


class TrainingMode(StrEnum):
    WORD_TRANSLATION = "word_translation"
    VERB_TRANSLATION = "verb_translation"
    CONJUGATION = "conjugation"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class BadgeRarity(StrEnum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    profile: Mapped[UserProfile | None] = relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    progresses: Mapped[list[UserProgress]] = relationship(
        "UserProgress", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[TrainingSession]] = relationship(
        "TrainingSession", back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage", back_populates="user", cascade="all, delete-orphan"
    )
    badges: Mapped[list[UserBadge]] = relationship(
        "UserBadge", back_populates="user", cascade="all, delete-orphan"
    )
    xp_events: Mapped[list[XPEvent]] = relationship(
        "XPEvent", back_populates="user", cascade="all, delete-orphan"
    )
    challenge_progresses: Mapped[list[UserChallengeProgress]] = relationship(
        "UserChallengeProgress", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[UserPreference | None] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    outgoing_friend_links: Mapped[list[FriendLink]] = relationship(
        "FriendLink",
        back_populates="user",
        foreign_keys="FriendLink.user_id",
        cascade="all, delete-orphan",
    )
    incoming_friend_links: Mapped[list[FriendLink]] = relationship(
        "FriendLink",
        back_populates="friend",
        foreign_keys="FriendLink.friend_user_id",
        cascade="all, delete-orphan",
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    theme_preference: Mapped[str] = mapped_column(String(16), default="arcade")

    user: Mapped[User] = relationship("User", back_populates="profile")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    sound_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mother_tongue_language_id: Mapped[int | None] = mapped_column(
        ForeignKey("languages.id", ondelete="SET NULL"), nullable=True
    )
    learning_language_id: Mapped[int | None] = mapped_column(
        ForeignKey("languages.id", ondelete="SET NULL"), nullable=True
    )
    translation_display_mode: Mapped[str] = mapped_column(String(32), default="partial")
    force_unlock_added_words: Mapped[bool] = mapped_column(Boolean, default=False)
    last_practice_pair: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_practice_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped[User] = relationship("User", back_populates="preferences")


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    pronoun_set: Mapped[list[str]] = mapped_column(JSON, default=list)
    tense_definitions: Mapped[dict[str, dict[str, str]]] = mapped_column(JSON, default=dict)
    difficulty_tiers: Mapped[dict[str, list[str]]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(128), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="RESTRICT"), index=True)

    translations: Mapped[list[WordTranslation]] = relationship(
        "WordTranslation", back_populates="word", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("text", "language_id", name="uq_words_text_language"),)


class WordTranslation(Base):
    __tablename__ = "word_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), index=True)
    target_language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="RESTRICT"), index=True)
    translation: Mapped[str] = mapped_column(String(128), index=True)
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(64), default="legacy_csv")

    word: Mapped[Word] = relationship("Word", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("word_id", "target_language_id", "translation", name="uq_word_translation"),
    )


class Verb(Base):
    __tablename__ = "verbs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    infinitive: Mapped[str] = mapped_column(String(128), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="RESTRICT"), index=True)

    translations: Mapped[list[VerbTranslation]] = relationship(
        "VerbTranslation", back_populates="verb", cascade="all, delete-orphan"
    )
    conjugations: Mapped[list[VerbConjugation]] = relationship(
        "VerbConjugation", back_populates="verb", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("infinitive", "language_id", name="uq_verbs_infinitive_language"),)


class VerbTranslation(Base):
    __tablename__ = "verb_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verb_id: Mapped[int] = mapped_column(ForeignKey("verbs.id", ondelete="CASCADE"), index=True)
    target_language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="RESTRICT"), index=True)
    translation: Mapped[str] = mapped_column(String(128), index=True)
    synonyms: Mapped[list[str]] = mapped_column(JSON, default=list)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(64), default="legacy_csv")

    verb: Mapped[Verb] = relationship("Verb", back_populates="translations")

    __table_args__ = (
        UniqueConstraint("verb_id", "target_language_id", "translation", name="uq_verb_translation"),
    )


class VerbConjugation(Base):
    __tablename__ = "verb_conjugations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    verb_id: Mapped[int] = mapped_column(ForeignKey("verbs.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id", ondelete="RESTRICT"), index=True)
    mood: Mapped[str] = mapped_column(String(64), index=True)
    tense: Mapped[str] = mapped_column(String(128), index=True)
    pronoun: Mapped[str] = mapped_column(String(32), index=True)
    conjugated_form: Mapped[str] = mapped_column(String(128))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(64), default="legacy_csv")

    verb: Mapped[Verb] = relationship("Verb", back_populates="conjugations")

    __table_args__ = (
        UniqueConstraint(
            "verb_id",
            "language_id",
            "mood",
            "tense",
            "pronoun",
            name="uq_verb_conjugation_slot",
        ),
        Index("idx_conjugations_lookup", "verb_id", "language_id", "tense"),
    )


class UserProgress(Base):
    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_type: Mapped[ProgressItemType] = mapped_column(Enum(ProgressItemType, native_enum=False), index=True)
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    language_pair: Mapped[str] = mapped_column(String(16), index=True)
    probability: Mapped[float] = mapped_column(Float, default=1000.0)
    times_seen: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship("User", back_populates="progresses")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "item_type",
            "item_id",
            "language_pair",
            name="uq_user_progress_slot",
        ),
        Index("idx_progress_unlock", "user_id", "item_type", "language_pair", "unlocked"),
        Index("idx_progress_probability", "user_id", "item_type", "language_pair", "probability"),
    )


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[TrainingMode] = mapped_column(Enum(TrainingMode, native_enum=False), index=True)
    language_pair: Mapped[str] = mapped_column(String(16), index=True)
    config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="sessions")
    items: Mapped[list[SessionItem]] = relationship(
        "SessionItem", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_sessions_active", "user_id", "mode", "completed_at"),)


class SessionItem(Base):
    __tablename__ = "session_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id", ondelete="CASCADE"), index=True)
    item_type: Mapped[ProgressItemType] = mapped_column(Enum(ProgressItemType, native_enum=False), index=True)
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    multiplier_applied: Mapped[float] = mapped_column(Float, default=1.0)
    meta: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[TrainingSession] = relationship("TrainingSession", back_populates="items")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, native_enum=False), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="chat_messages")


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    feature: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(64), index=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    input_cost_per_million: Mapped[float] = mapped_column(Float, default=0.0)
    output_cost_per_million: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[str] = mapped_column(String(32), default="success", index=True)
    request_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extra_data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class XPEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(64), index=True)
    meta: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped[User] = relationship("User", back_populates="xp_events")


class BadgeDefinition(Base):
    __tablename__ = "badge_definitions"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(32), default="badge")
    rarity: Mapped[BadgeRarity] = mapped_column(Enum(BadgeRarity, native_enum=False), default=BadgeRarity.COMMON)
    metric_key: Mapped[str] = mapped_column(String(64), index=True)
    threshold: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list[UserBadge]] = relationship("UserBadge", back_populates="badge")


class UserBadge(Base):
    __tablename__ = "user_badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    badge_code: Mapped[str] = mapped_column(ForeignKey("badge_definitions.code", ondelete="CASCADE"), index=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="badges")
    badge: Mapped[BadgeDefinition] = relationship("BadgeDefinition", back_populates="users")

    __table_args__ = (UniqueConstraint("user_id", "badge_code", name="uq_user_badge_slot"),)


class WeeklyChallenge(Base):
    __tablename__ = "weekly_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(32), default="target")
    metric_key: Mapped[str] = mapped_column(String(64), index=True)
    target_value: Mapped[int] = mapped_column(Integer, default=1)
    reward_xp: Mapped[int] = mapped_column(Integer, default=100)
    starts_at: Mapped[date] = mapped_column(Date, index=True)
    ends_at: Mapped[date] = mapped_column(Date, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    progresses: Mapped[list[UserChallengeProgress]] = relationship(
        "UserChallengeProgress", back_populates="challenge", cascade="all, delete-orphan"
    )


class UserChallengeProgress(Base):
    __tablename__ = "user_challenge_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("weekly_challenges.id", ondelete="CASCADE"), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reward_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="challenge_progresses")
    challenge: Mapped[WeeklyChallenge] = relationship("WeeklyChallenge", back_populates="progresses")

    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge_slot"),
    )


class FriendLink(Base):
    __tablename__ = "friend_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    friend_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship("User", back_populates="outgoing_friend_links", foreign_keys=[user_id])
    friend: Mapped[User] = relationship("User", back_populates="incoming_friend_links", foreign_keys=[friend_user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "friend_user_id", name="uq_friend_link"),
    )


class WordLexicalEntry(Base):
    __tablename__ = "word_lexical_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), unique=True, index=True
    )
    definition: Mapped[str] = mapped_column(Text)
    synonyms: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)
    examples: Mapped[list[str]] = mapped_column(JSON, default=list)
    extended_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="ai")
    flag_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WordNativeTranslation(Base):
    __tablename__ = "word_native_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), index=True)
    native_language_id: Mapped[int] = mapped_column(
        ForeignKey("languages.id", ondelete="RESTRICT"), index=True
    )
    translation: Mapped[str] = mapped_column(String(256))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(64), default="ai")
    flag_count: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "word_id", "native_language_id", "translation", name="uq_word_native_translation"
        ),
    )


class UserAddedWord(Base):
    __tablename__ = "user_added_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), index=True)
    language_pair: Mapped[str] = mapped_column(String(16), index=True)
    context_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", "language_pair", name="uq_user_added_word"),
    )


class TranslationReport(Base):
    __tablename__ = "translation_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    entry_type: Mapped[str] = mapped_column(String(16))  # 'lexical' | 'native'
    entry_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(32), default="thematic")
    # thematic | grammatical | verb_semantic | register | difficulty | user
    applies_to: Mapped[list[str]] = mapped_column(JSON, default=list)
    # word | verb
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WordTag(Base):
    __tablename__ = "word_tags"

    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(32), default="user")
    # ai_suggested | user | system_curated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VerbTag(Base):
    __tablename__ = "verb_tags"

    verb_id: Mapped[int] = mapped_column(
        ForeignKey("verbs.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(32), default="user")
    # ai_suggested | user | system_curated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WordSet(Base):
    __tablename__ = "word_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kind: Mapped[str] = mapped_column(String(16), default="manual")
    # manual | smart
    filter_tag_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    # For smart sets: words matching ALL of these tag ids are included.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WordSetMember(Base):
    __tablename__ = "word_set_members"

    set_id: Mapped[int] = mapped_column(
        ForeignKey("word_sets.id", ondelete="CASCADE"), primary_key=True
    )
    word_id: Mapped[int] = mapped_column(
        ForeignKey("words.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
