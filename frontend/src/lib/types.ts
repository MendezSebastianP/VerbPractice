export type ThemeName = 'light' | 'dark' | 'arcade';

export interface UserProfileState {
  xp: number;
  level: number;
  streak_days: number;
  last_active_date: string | null;
  theme_preference: ThemeName;
}

export interface UserState {
  id: number;
  username: string;
  is_admin: boolean;
  profile: UserProfileState;
}

export interface BootPayload {
  app_name: string;
  authenticated: boolean;
  csrf_token: string;
  theme: ThemeName;
  user: UserState | null;
  preferences: {
    sound_enabled: boolean;
    show_shortcuts: boolean;
  };
  entry_path: string;
}

export interface FocusItem {
  label: string;
  translation?: string | null;
  item_type: string;
  language_pair: string;
  probability: number;
  times_seen: number;
  times_correct: number;
  accuracy: number | null;
  streak: number;
}

export interface DashboardPayload {
  user: UserState;
  theme: ThemeName;
  preferences: {
    sound_enabled: boolean;
    show_shortcuts: boolean;
  };
  overall: {
    total: number;
    unlocked: number;
    mastered: number;
    practiced: number;
    avg_probability: number;
    focus_items: FocusItem[];
  };
  mode_cards: Array<{
    mode: string;
    title: string;
    href: string;
    description: string;
    pair_label: string;
    total: number;
    unlocked: number;
    mastered: number;
    practiced: number;
    avg_probability: number;
    focus_items: FocusItem[];
  }>;
  completed_sessions: number;
  today_sessions: number;
  recent_sessions: Array<{
    id: number;
    mode: string;
    language_pair: string;
    score: number | null;
    started_at: string | null;
    completed_at: string | null;
  }>;
  active_sessions: Array<{
    title: string;
    href: string;
    progress_current: number;
    progress_total: number;
    started_at: string | null;
    language_pair: string;
  }>;
  mode_counts: Record<string, number>;
  recent_messages: Array<{
    id: number;
    role: string;
    content: string;
    created_at: string | null;
  }>;
  gamification: {
    sound_enabled: boolean;
    badges: Array<{
      code: string;
      title: string;
      description: string;
      icon: string;
      rarity: string;
      unlocked_at: string | null;
    }>;
    weekly_challenge: {
      slug: string;
      title: string;
      description: string;
      icon: string;
      metric_key: string;
      target_value: number;
      reward_xp: number;
      starts_at: string;
      ends_at: string;
      progress: number;
      completed: boolean;
      completed_at: string | null;
    };
    global_leaderboard: Array<{
      username: string;
      level: number;
      xp: number;
      streak_days: number;
    }>;
    weekly_leaderboard: Array<{
      username: string;
      weekly_xp: number;
    }>;
    circle: {
      friends: Array<{
        user_id: number;
        username: string;
      }>;
      leaderboard: Array<{
        user_id: number;
        username: string;
        level: number;
        xp: number;
      }>;
    };
    recent_xp: Array<{
      amount: number;
      reason: string;
      created_at: string | null;
    }>;
  };
}

export interface RewardState {
  gained_xp: number;
  old_level: number;
  new_level: number;
  leveled_up: boolean;
  unlocked_badges: Array<{
    code: string;
    title: string;
    description: string;
    icon: string;
    rarity: string;
    unlocked_at: string | null;
  }>;
  challenge: {
    slug: string;
    title: string;
    description: string;
    icon: string;
    metric_key: string;
    target_value: number;
    reward_xp: number;
    starts_at: string;
    ends_at: string;
    progress: number;
    completed: boolean;
    completed_at: string | null;
  } | null;
  combo: number | null;
  best_combo: number | null;
}

export interface TranslationState {
  mode: string;
  slug: 'words' | 'verbs';
  title: string;
  setup: boolean;
  finished?: boolean;
  feedback?: string | null;
  direction_label: string;
  defaults: {
    length: number;
    direction: string;
  };
  overview: {
    total: number;
    unlocked: number;
    mastered: number;
    practiced: number;
    avg_probability: number;
    focus_items: FocusItem[];
  };
  session?: {
    id: number;
    direction: string;
    length: number;
    progress_current: number;
    progress_total: number;
    combo: number;
    best_combo: number;
  };
  question?: {
    item_id: number;
    prompt: string;
    // Present so the client can run the quick-shot locally (auto-advance on a
    // perfect first attempt). Server grading stays authoritative.
    accepted_answers?: string[];
    synonym_answers?: string[];
  };
  hint?: string;
  result?: {
    finished?: boolean;
    feedback?: string;
    is_correct?: boolean;
    is_synonym?: boolean;
    gamification?: RewardState;
  } | null;
}

export interface StudyTranslationEntry {
  item_id: number;
  prompt: string;
  answer: string;
  group: 'newest' | 'focus';
  score: number;
}

export interface StudyConjugationEntry {
  item_id: number;
  prompt: string;
  group: 'newest' | 'focus';
  score: number;
  language: string;
  tenses: Array<{
    tense: string;
    forms: Array<{ pronoun: string; form: string }>;
  }>;
}

export interface StudyPoolResponse {
  mode: 'words' | 'verbs' | 'conjugation';
  entries: Array<StudyTranslationEntry | StudyConjugationEntry>;
}

export interface LanguageConfig {
  code: string;
  name: string;
  pronoun_set: string[];
  difficulty_tiers: Record<string, string[]>;
  tense_definitions: Record<string, { mood: string }>;
  available: boolean;
  available_tenses: string[];
  tense_verb_counts: Record<string, number>;
  verb_count: number;
}

export interface ConjugationTenseReview {
  verb_id: number;
  verb: string;
  tense: string;
  correct: number;
  total: number;
  accuracy: number;
  cells: Array<{
    pronoun: string;
    kind: 'missing' | 'prefilled' | 'answer' | 'linked';
    answer: string;
    expected: string;
    correct: boolean | null;
    linked_to?: string;
    group_pronouns?: string[];
    prefilled?: boolean;
  }>;
}

export interface ConjugationState {
  mode: string;
  slug: 'conjugation';
  title: string;
  setup: boolean;
  finished?: boolean;
  feedback?: string | null;
  overview: {
    total: number;
    unlocked: number;
    mastered: number;
    practiced: number;
    avg_probability: number;
    focus_items: FocusItem[];
  };
  languages: LanguageConfig[];
  session?: {
    id: number;
    language: string;
    level: string;
    fill_level: string;
    length: number;
    selected_tenses: string[];
    progress_current: number;
    progress_total: number;
    combo: number;
    best_combo: number;
    checked_tenses?: string[];
  };
  question?: {
    verb_id: number;
    verb: string;
    selected_tenses: string[];
    pronouns: string[];
    form_groups: Record<string, Array<{
      representative: string;
      pronouns: string[];
    }>>;
    rows: Array<{
      pronoun: string;
      cells: Array<{
        tense: string;
        kind: 'missing' | 'prefilled' | 'input' | 'linked';
        value: string | null;
        accepted_answers?: string[];
        prefilled: boolean;
        representative: string | null;
        linked_to?: string;
        group_pronouns: string[];
        group_size: number;
        group_count: number;
      }>;
    }>;
  };
  result?: {
    finished?: boolean;
    accuracy?: number;
    correct?: number;
    total?: number;
    session_score?: number | null;
    session_length?: number;
    best_combo?: number;
    review?: {
      verb_id: number;
      verb: string;
      selected_tenses: string[];
      rows: Array<{
        pronoun: string;
        cells: Array<{
          tense: string;
          kind: 'missing' | 'prefilled' | 'answer' | 'linked';
          answer: string;
          expected: string;
          correct: boolean | null;
          linked_to?: string;
          group_pronouns?: string[];
          prefilled?: boolean;
        }>;
      }>;
    };
    gamification?: RewardState;
  } | null;
}

export interface ChatPayload {
  messages: Array<{
    id: number;
    role: string;
    content: string;
    created_at: string | null;
  }>;
  focus_items: FocusItem[];
  suggestions: string[];
  api_enabled: boolean;
}

export interface MonitorPayload {
  viewer: string;
  totals: Record<string, number>;
  users: Array<{
    id: number;
    username: string;
    level: number;
    xp: number;
    streak_days: number;
    theme: string;
  }>;
  active_sessions: Array<Record<string, unknown>>;
  recent_sessions: Array<Record<string, unknown>>;
  recent_items: Array<Record<string, unknown>>;
  progress_rows: Array<Record<string, unknown>>;
  recent_messages: Array<Record<string, unknown>>;
}

export interface AdminContentSummaryPayload {
  viewer: string;
  summary: {
    words: { total: number; needs_review: number };
    verbs: { total: number; needs_review: number };
    conjugations: { total: number; needs_review: number };
    curated: {
      inventory_links: number;
      batches_total: number;
      batches_with_authored: number;
      batches_import_ready: number;
      required_slots: number;
      authored_slots: number;
      reviewed_slots: number;
      approved_slots: number;
      authored_pct: number;
      reviewed_pct: number;
      approved_pct: number;
      batches: Array<{
        batch: number;
        required_slots: number;
        authored_slots: number;
        reviewed_slots: number;
        approved_slots: number;
        authored_pct: number;
        reviewed_pct: number;
        approved_pct: number;
        import_ready: boolean;
      }>;
    };
  };
}

export interface AdminAiUsagePayload {
  viewer: string;
  financials: {
    total_cost_usd: number;
    translation_cost_usd: number;
    average_translation_cost_usd: number;
    total_calls: number;
    translation_calls: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    translation_tokens: number;
  };
  by_feature: Array<{
    feature: string;
    label: string;
    calls: number;
    cost_usd: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    average_cost_usd: number;
  }>;
  by_model: Array<{
    model: string;
    calls: number;
    cost_usd: number;
    total_tokens: number;
    input_cost_per_million: number;
    output_cost_per_million: number;
  }>;
  top_users: Array<{
    username: string;
    calls: number;
    total_cost_usd: number;
  }>;
  recent: Array<{
    id: number;
    user: string | null;
    feature: string;
    label: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    cost_usd: number;
    request_label: string | null;
    status: string;
    created_at: string | null;
    extra_data: Record<string, unknown>;
  }>;
  pricing: Array<{
    model: string;
    input_cost_per_million: number;
    output_cost_per_million: number;
  }>;
}

export interface AdminWordRow {
  id: number;
  word_id: number;
  text: string;
  language_code: string;
  language_name: string;
  translation: string;
  target_language_code: string;
  target_language_name: string;
  synonyms: string[];
  verified: boolean;
  source: string;
}

export interface AdminVerbRow {
  id: number;
  verb_id: number;
  infinitive: string;
  language_code: string;
  language_name: string;
  translation: string;
  target_language_code: string;
  target_language_name: string;
  synonyms: string[];
  verified: boolean;
  source: string;
}

export interface AdminConjugationRow {
  id: number;
  verb_id: number;
  infinitive: string;
  language_code: string;
  language_name: string;
  mood: string;
  tense: string;
  pronoun: string;
  conjugated_form: string;
  verified: boolean;
  source: string;
}

export interface LanguageEntry {
  id: number;
  code: string;
  name: string;
}

export interface TagEntry {
  id: number;
  slug: string;
  display_name: string;
  kind: string;
  applies_to: string[];
}

export interface WordSetSummary {
  id: number;
  name: string;
  description: string | null;
  icon: string | null;
  kind: 'manual' | 'smart';
  owner_user_id: number | null;
  filter_tag_slugs: string[];
  word_count: number;
}

export interface WordSetDetail extends WordSetSummary {
  words: Array<{
    word_id: number;
    text: string;
    language_code: string;
  }>;
}

export type TranslationDisplayMode = 'mother_full' | 'partial' | 'learning_full';

// Last-used game setup per trainer, restored on the next visit. Keys are
// practice modes ('word_translation' | 'verb_translation' | 'conjugation');
// values are trainer-specific (length, tenses, …).
export interface TranslationTrainerSetup {
  length?: number;
}

export interface ConjugationTrainerSetup {
  language?: string;
  level?: string;
  fill_level?: string;
  length?: number;
  selected_tenses?: string[];
}

export interface TrainerSetups {
  word_translation?: TranslationTrainerSetup;
  verb_translation?: TranslationTrainerSetup;
  conjugation?: ConjugationTrainerSetup;
}

export interface UserSettings {
  sound_enabled: boolean;
  show_shortcuts: boolean;
  mother_tongue: LanguageEntry | null;
  learning_language: LanguageEntry | null;
  translation_display_mode: TranslationDisplayMode;
  force_unlock_added_words: boolean;
  last_practice_pair: string | null;
  last_practice_mode: string | null;
  trainer_setups: TrainerSetups | null;
}

export interface UserSettingsPatch {
  mother_tongue_code: string;
  learning_language_code: string;
  translation_display_mode: TranslationDisplayMode;
  force_unlock_added_words: boolean;
  show_shortcuts: boolean;
  last_practice_pair: string;
  last_practice_mode: string;
  trainer_setup: {
    mode: 'word_translation' | 'verb_translation' | 'conjugation';
    setup: TranslationTrainerSetup | ConjugationTrainerSetup;
  };
}

export interface LexicalEntry {
  id: number | null;
  word_id: number;
  definition: string;
  synonyms: Array<{ text: string; gloss?: string }>;
  examples: string[];
  extended_content: string | null;
}

export interface NativeTranslation {
  id: number | null;
  word_id: number;
  native_language_code: string;
  translation: string;
  note: string | null;
}

export type AddWordStatus = 'exact' | 'corrected' | 'ambiguous' | 'not_found';
export interface DisplayDefinition {
  text: string;
  language_code: string;
}

export interface AddedWordResult {
  status: AddWordStatus;
  original_input: string;
  detected_input_language: string | null;
  word_id: number;
  text: string;
  learning_language_code: string;
  mother_tongue_code: string;
  lexical: LexicalEntry;
  definition_language_code: string;
  display_definition: DisplayDefinition;
  lookup_mode: 'definition' | 'translation';
  practice_eligible: boolean;
  natives: NativeTranslation[];
  general_note: string | null;
  question_answer: string | null;
  part_of_speech: string | null;
  cefr_level: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2' | null;
  selected_sense_id: number | null;
  sense_candidates: {
    id: number;
    sense_key: string;
    definition: string;
    part_of_speech: string | null;
  }[];
  ranking: {
    method: string | null;
    score: number | null;
    margin: number | null;
  };
  reportable: boolean;
  suggested_tags: string[];
  priority_queue_id: number | null;
  lookup_id: number;
  force_unlocked: boolean;
}

export type SenseSelectionResult = Pick<
  AddedWordResult,
  | 'lexical'
  | 'definition_language_code'
  | 'display_definition'
  | 'natives'
  | 'question_answer'
  | 'part_of_speech'
  | 'cefr_level'
  | 'selected_sense_id'
  | 'sense_candidates'
  | 'ranking'
  | 'reportable'
>;

export interface AddedWordNotFound {
  status: 'not_found';
  suggestions: string[];
  original_input: string;
  learning_language_code: string;
  mother_tongue_code: string;
}

export type AddWordResponse = AddedWordResult | AddedWordNotFound;

export interface OcrWordResult {
  text: string;
  confidence: number;
  box: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export interface OcrResponse {
  text: string;
  lines: string[];
  mean_confidence: number | null;
  ocr_lang: string;
  words: OcrWordResult[];
}

export interface UserWordEntry {
  word_id: number;
  text: string;
  translation: string | null;
  definition: string | null;
  lookup_mode: 'definition' | 'translation';
  in_progress: boolean;
  unlocked: boolean;
  probability: number | null;
  added_at: string | null;
}

export interface WordHistoryEntry {
  added_id: number;
  word_id: number;
  text: string;
  language_pair: string;
  learning_language_code: string;
  mother_tongue_code: string;
  added_at: string | null;
  lexical: LexicalEntry;
  definition_language_code: string;
  display_definition: DisplayDefinition;
  lookup_mode: 'definition' | 'translation';
  practice_eligible: boolean;
  natives: NativeTranslation[];
  context: string | null;
  question: string | null;
  question_answer: string | null;
  selected_sense_id: number | null;
  tags: string[];
}

export interface PriorityQueueEntry {
  id: number;
  word_id: number;
  word_text: string;
  language_pair: string;
  context_hint: string | null;
  added_at: string;
}

export interface CommunityPayload {
  sound_enabled: boolean;
  badges: DashboardPayload['gamification']['badges'];
  weekly_challenge: DashboardPayload['gamification']['weekly_challenge'];
  global_leaderboard: DashboardPayload['gamification']['global_leaderboard'];
  weekly_leaderboard: DashboardPayload['gamification']['weekly_leaderboard'];
  circle: DashboardPayload['gamification']['circle'];
  recent_xp: DashboardPayload['gamification']['recent_xp'];
}

export interface SemanticGradePayload {
  csrf_token: string;
  challenge_id:
    | 'se_retrouver'
    | 'tutoyer'
    | 'flaner'
    | 'depanner'
    | 's_attarder'
    | 'madrugar'
    | 'estrenar'
    | 'empalagar'
    | 'trasnochar'
    | 'anorar';
  answer: string;
}

export interface SemanticGradeResponse {
  verdict: 'correct' | 'partial' | 'incorrect' | 'uncertain';
  exact_match: boolean;
  answer_quality: 'complete' | 'concise' | null;
  method: string;
  latency_ms: number;
  model_available: boolean;
  model_name: string;
  positive_score: number;
  negative_score: number | null;
  margin: number | null;
  concept_coverage: number;
  matched_reference: {
    text: string;
    score: number;
  };
  required_concepts: Array<{
    label: string;
    score: number;
    matched_example: string;
    covered: boolean;
    evidence: 'semantic' | 'explicit' | 'context' | 'optional_omitted' | 'missing';
  }>;
  hard_negatives: Array<{
    label: string;
    score: number;
    matched_example: string;
    triggered: boolean;
    explicitly_rejected: boolean;
  }>;
  negation_guard: {
    mismatch: boolean;
    corrective_contrast: boolean;
    answer_markers: string[];
    reference_markers: string[];
  };
  verification: {
    available: boolean;
    model_name: string;
    checked: boolean;
    entailment_score: number | null;
    contradiction_score: number | null;
    negative_entailment_score: number | null;
    entailment_margin: number | null;
    matched_reference: string | null;
    overflow: boolean;
    safety_flags: string[];
    confirmed_axes: string[];
  };
  thresholds: Record<string, number>;
  reasons: string[];
}
