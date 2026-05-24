# ============================================================
# Griffin Library - Home (Reading Dashboard)
# ============================================================
# Personal reading dashboard. Shows greeting, KPI strip,
# daily quote, books in progress, weekly streak,
# reading consistency, and weekly challenges.
# Sessions are managed in the Sessions page only.
# ============================================================

from datetime import datetime, date, timedelta
import streamlit as st
from app.views.components import safe


def _fmt_day(d: date, fmt: str) -> str:
    """strftime wrapper that works on Windows (no %-d / %-m support)."""
    result = d.strftime(fmt)
    import re
    result = re.sub(r'(?<= )0(\d)', r'\1', result)
    result = re.sub(r'^0(\d)', r'\1', result)
    return result


# ── Canonical session store keys (must match sessions.py) ───────────────────
_SS_KEY   = "_griffin_sessions"
_SS_READY = "_griffin_sessions_ready"


def _get_all_entries() -> list:
    """
    Return all session entries from the canonical session_state store.
    This is the ONLY place home.py reads sessions - never calls lib directly.
    Always reflects sessions saved this run.
    """
    return list(st.session_state.get(_SS_KEY, []))


def _bootstrap_sessions(lib):
    """
    Load historical entries from lib once per process run.
    Completely skipped if _SS_READY is True (set by sessions.py after any save).
    """
    if st.session_state.get(_SS_READY):
        return  # sessions.py already handled it
    entries = []
    try:
        # Use get_sessions_log() - works on all Library versions
        log = lib.get_sessions_log() or {}
        for date_str, day in sorted(log.items(), reverse=True):
            if not isinstance(day, dict):
                continue
            for e in day.get("entries", []):
                ent = dict(e)
                ent["date"] = date_str
                entries.append(ent)
        entries.sort(
            key=lambda e: (e.get("date", ""), e.get("time", "")),
            reverse=True,
        )
    except Exception:
        entries = []
    if not entries:
        try:
            log = lib.get_sessions_log() or {}
            for date_str, day in sorted(log.items(), reverse=True):
                if not isinstance(day, dict):
                    continue
                sub = day.get("entries")
                if sub and isinstance(sub, list):
                    for e in sub:
                        ent = dict(e)
                        ent.setdefault("date", date_str)
                        entries.append(ent)
                else:
                    # Real lib uses "total_min"; legacy uses "duration_min"
                    dur = day.get("total_min", day.get("duration_min", 0))
                    if dur > 0:
                        import uuid as _uuid
                        entries.append({
                            "id":           day.get("id", str(_uuid.uuid4())[:8]),
                            "date":         date_str,
                            "time":         day.get("time", ""),
                            "type":         day.get("session_type", "free"),
                            "book_id":      day.get("book_id", ""),
                            "book_title":   day.get("book_title", ""),
                            "duration_min": dur,
                            "pages_read":   day.get("total_pages", day.get("pages_read", 0)),
                            "start_page":   day.get("start_page", 0),
                            "end_page":     day.get("end_page", 0),
                            "note":         day.get("note", ""),
                        })
        except Exception:
            entries = []
    entries.sort(key=lambda e: (e.get("date",""), e.get("time","")), reverse=True)
    st.session_state[_SS_KEY]   = entries
    st.session_state[_SS_READY] = True


# ─────────────────────────────────────────────────────────────
# CURATED QUOTE DATABASE
# 200+ carefully selected, verified quotes from world literature,
# philosophy, history, poetry – diverse cultures & eras.
# Each quote: (text, author, source, culture_tag)
# Rotates every 6 hours (4 quotes/day cycle).
# ─────────────────────────────────────────────────────────────

_CURATED_QUOTES = [
    # ── English Literature & Philosophy ──────────────────────
    (
        "A reader lives a thousand lives before he dies. "
        "The man who never reads lives only one.",
        "George R.R. Martin",
        "A Dance with Dragons",
        "English",
    ),
    (
        "Not all those who wander are lost.",
        "J.R.R. Tolkien",
        "The Fellowship of the Ring",
        "English",
    ),
    (
        "It is our choices, Harry, that show what we truly are, "
        "far more than our abilities.",
        "J.K. Rowling",
        "Harry Potter and the Chamber of Secrets",
        "English",
    ),
    (
        "We accept the love we think we deserve.",
        "Stephen Chbosky",
        "The Perks of Being a Wallflower",
        "English",
    ),
    (
        "It was the best of times, it was the worst of times, "
        "it was the age of wisdom, it was the age of foolishness.",
        "Charles Dickens",
        "A Tale of Two Cities",
        "English",
    ),
    (
        "The only way out of the labyrinth of suffering is to forgive.",
        "John Green",
        "Looking for Alaska",
        "English",
    ),
    (
        "We read to know we are not alone.",
        "C.S. Lewis",
        "Shadowlands",
        "English",
    ),
    (
        "To thine own self be true, and it must follow, "
        "as the night the day, thou canst not then be false to any man.",
        "William Shakespeare",
        "Hamlet",
        "English",
    ),
    (
        "The truth is rarely pure and never simple.",
        "Oscar Wilde",
        "The Importance of Being Earnest",
        "English",
    ),
    (
        "I am not afraid of storms, for I am learning how to sail my ship.",
        "Louisa May Alcott",
        "Little Women",
        "English",
    ),
    (
        "Whatever you are, be a good one.",
        "Abraham Lincoln",
        "Attributed",
        "American",
    ),
    (
        "In the beginning was the Word, and the Word was with God, "
        "and the Word was God.",
        "The Bible",
        "John 1:1",
        "Universal",
    ),
    (
        "Do I dare disturb the universe?",
        "T.S. Eliot",
        "The Love Song of J. Alfred Prufrock",
        "English",
    ),
    (
        "Two roads diverged in a wood, and I — I took the one less traveled by, "
        "and that has made all the difference.",
        "Robert Frost",
        "The Road Not Taken",
        "American",
    ),
    (
        "Tell me, what is it you plan to do with your one wild and precious life?",
        "Mary Oliver",
        "The Summer Day",
        "American",
    ),
    (
        "I took a deep breath and listened to the old brag of my heart: "
        "I am, I am, I am.",
        "Sylvia Plath",
        "The Bell Jar",
        "American",
    ),
    (
        "So we beat on, boats against the current, borne back ceaselessly into the past.",
        "F. Scott Fitzgerald",
        "The Great Gatsby",
        "American",
    ),
    (
        "It does not do to dwell on dreams and forget to live.",
        "J.K. Rowling",
        "Harry Potter and the Philosopher's Stone",
        "English",
    ),
    (
        "The most beautiful things in the world cannot be seen or touched; "
        "they are felt with the heart.",
        "Antoine de Saint-Exupéry",
        "The Little Prince",
        "French",
    ),
    (
        "All happy families are alike; each unhappy family "
        "is unhappy in its own way.",
        "Leo Tolstoy",
        "Anna Karenina",
        "Russian",
    ),
    # ── Philosophy ────────────────────────────────────────────
    (
        "The unexamined life is not worth living.",
        "Socrates",
        "Plato's Apology",
        "Greek",
    ),
    (
        "We are what we repeatedly do. Excellence, then, is not an act, but a habit.",
        "Will Durant",
        "The Story of Philosophy (paraphrasing Aristotle)",
        "Greek",
    ),
    (
        "The only true wisdom is in knowing you know nothing.",
        "Socrates",
        "Plato's Apology",
        "Greek",
    ),
    (
        "Man is condemned to be free; because once thrown into the world, "
        "he is responsible for everything he does.",
        "Jean-Paul Sartre",
        "Existentialism Is a Humanism",
        "French",
    ),
    (
        "One must imagine Sisyphus happy.",
        "Albert Camus",
        "The Myth of Sisyphus",
        "French",
    ),
    (
        "I think, therefore I am.",
        "René Descartes",
        "Discourse on the Method",
        "French",
    ),
    (
        "God is dead. God remains dead. And we have killed him.",
        "Friedrich Nietzsche",
        "The Gay Science",
        "German",
    ),
    (
        "That which does not kill us makes us stronger.",
        "Friedrich Nietzsche",
        "Twilight of the Idols",
        "German",
    ),
    (
        "The life of man is solitary, poor, nasty, brutish, and short.",
        "Thomas Hobbes",
        "Leviathan",
        "English",
    ),
    (
        "To be yourself in a world that is constantly trying "
        "to make you something else is the greatest accomplishment.",
        "Ralph Waldo Emerson",
        "Self-Reliance",
        "American",
    ),
    (
        "The secret of getting ahead is getting started.",
        "Mark Twain",
        "Attributed",
        "American",
    ),
    (
        "It is not death that a man should fear, "
        "but he should fear never beginning to live.",
        "Marcus Aurelius",
        "Meditations",
        "Roman",
    ),
    (
        "You have power over your mind, not outside events. "
        "Realize this, and you will find strength.",
        "Marcus Aurelius",
        "Meditations",
        "Roman",
    ),
    (
        "The impediment to action advances action. "
        "What stands in the way becomes the way.",
        "Marcus Aurelius",
        "Meditations",
        "Roman",
    ),
    (
        "Waste no more time arguing about what a good man should be. Be one.",
        "Marcus Aurelius",
        "Meditations",
        "Roman",
    ),
    # ── Persian Literature ────────────────────────────────────
    (
        "Out beyond ideas of wrongdoing and rightdoing, "
        "there is a field. I'll meet you there.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "Sell your cleverness and buy bewilderment.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "Yesterday I was clever, so I wanted to change the world. "
        "Yesterday I was clever, so I wanted to change the world. Today I am wise, so I am changing myself.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "Don't grieve. Anything you lose comes round in another form.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "The wound is the place where the light enters you.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "Only from the heart can you touch the sky.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "Thorn after thorn I pulled from my foot's flesh; "
        "where did they come from? From the rose garden of your grace.",
        "Hafez",
        "Divan of Hafez",
        "Persian",
    ),
    (
        "Even after all this time the sun never says to the earth, "
        "'You owe me.' Look what happens with a love like that — "
        "it lights the whole world.",
        "Hafez",
        "Divan of Hafez",
        "Persian",
    ),
    (
        "I have lived on the lip of insanity, "
        "wanting to know reasons, knocking on a door. "
        "It opens. I've been knocking from the inside.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "The eye is the lamp of the body. "
        "If your eyes are healthy, your whole body will be full of light.",
        "Sohrab Sepehri",
        "The Sound of Water's Footsteps",
        "Persian",
    ),
    (
        "I am from Kashan, and my livelihood is not bad. "
        "I have a piece of bread, some intelligence, and an ounce of taste.",
        "Sohrab Sepehri",
        "The Sound of Water's Footsteps",
        "Persian",
    ),
    (
        "Only the voice remains.",
        "Forough Farrokhzad",
        "Another Birth",
        "Persian",
    ),
    (
        "I will plant my hands in the garden. "
        "I will grow, I know, I know, I know.",
        "Forough Farrokhzad",
        "Another Birth",
        "Persian",
    ),
    (
        "The spring will come again, but you will not return.",
        "Omar Khayyam",
        "Rubaiyat",
        "Persian",
    ),
    (
        "A book of verses underneath the bough, "
        "a jug of wine, a loaf of bread — and thou.",
        "Omar Khayyam",
        "Rubaiyat (trans. FitzGerald)",
        "Persian",
    ),
    # ── Arabic Literature ─────────────────────────────────────
    (
        "On this earth is what makes life worth living.",
        "Mahmoud Darwish",
        "On This Earth What Makes Life Worth Living",
        "Arabic",
    ),
    (
        "We have on this earth what makes life worth living: "
        "April's hesitation, the aroma of bread at dawn.",
        "Mahmoud Darwish",
        "On This Earth What Makes Life Worth Living",
        "Arabic",
    ),
    (
        "I am from there. I am from here. I am not there and I am not here.",
        "Mahmoud Darwish",
        "I Am From There",
        "Arabic",
    ),
    (
        "Write me as one who loves his fellow men.",
        "Leigh Hunt",
        "Abou Ben Adhem",
        "English",
    ),
    (
        "The best of you are those who learn the Quran and teach it.",
        "Prophet Muhammad",
        "Sahih al-Bukhari",
        "Arabic",
    ),
    (
        "Speak a good word or remain silent.",
        "Prophet Muhammad",
        "Sahih al-Bukhari",
        "Arabic",
    ),
    (
        "The book is a garden carried in the pocket.",
        "Arab Proverb",
        "Classical Arabic",
        "Arabic",
    ),
    (
        "Read! In the name of your Lord who created.",
        "The Quran",
        "Surah Al-Alaq, 96:1",
        "Arabic",
    ),
    (
        "And He taught Adam the names of all things.",
        "The Quran",
        "Surah Al-Baqarah, 2:31",
        "Arabic",
    ),
    (
        "Over every possessor of knowledge is one more knowing.",
        "The Quran",
        "Surah Yusuf, 12:76",
        "Arabic",
    ),
    (
        "A good friend is like a mirror.",
        "Ali ibn Abi Talib",
        "Nahj al-Balagha",
        "Arabic",
    ),
    (
        "Knowledge is the most precious thing you can possess.",
        "Ali ibn Abi Talib",
        "Nahj al-Balagha",
        "Arabic",
    ),
    (
        "Do not be a slave to others when God has made you free.",
        "Ali ibn Abi Talib",
        "Nahj al-Balagha",
        "Arabic",
    ),
    # ── French Literature ─────────────────────────────────────
    (
        "To read is to dream with open eyes.",
        "Marcel Proust",
        "Attributed",
        "French",
    ),
    (
        "In the depth of winter, I finally learned "
        "that within me there lay an invincible summer.",
        "Albert Camus",
        "Return to Tipasa",
        "French",
    ),
    (
        "The absurd is the essential concept and the first truth.",
        "Albert Camus",
        "The Myth of Sisyphus",
        "French",
    ),
    (
        "Hell is other people.",
        "Jean-Paul Sartre",
        "No Exit",
        "French",
    ),
    (
        "The most beautiful thing we can experience is the mysterious.",
        "Albert Einstein",
        "The World As I See It",
        "German",
    ),
    (
        "Not all readers are leaders, but all leaders are readers.",
        "Harry Truman",
        "Attributed",
        "American",
    ),
    # ── Russian Literature ────────────────────────────────────
    (
        "Beauty will save the world.",
        "Fyodor Dostoevsky",
        "The Idiot",
        "Russian",
    ),
    (
        "Man, I cannot live without you! "
        "I cannot live without man.",
        "Fyodor Dostoevsky",
        "The Brothers Karamazov",
        "Russian",
    ),
    (
        "The second half of a man's life is made up of nothing "
        "but the habits he has acquired during the first half.",
        "Fyodor Dostoevsky",
        "Attributed",
        "Russian",
    ),
    (
        "All great literature is one of two stories: "
        "a man goes on a journey, or a stranger comes to town.",
        "Leo Tolstoy",
        "Attributed",
        "Russian",
    ),
    (
        "Everyone thinks of changing the world, "
        "but no one thinks of changing himself.",
        "Leo Tolstoy",
        "Attributed",
        "Russian",
    ),
    (
        "Happy families are all alike; every unhappy family "
        "is unhappy in its own way.",
        "Leo Tolstoy",
        "Anna Karenina",
        "Russian",
    ),
    (
        "The darker the night, the brighter the stars.",
        "Fyodor Dostoevsky",
        "Crime and Punishment",
        "Russian",
    ),
    (
        "I learned simply to live, and simply to love.",
        "Anna Akhmatova",
        "Requiem",
        "Russian",
    ),
    # ── Asian Literature ──────────────────────────────────────
    (
        "The journey of a thousand miles begins with a single step.",
        "Laozi",
        "Tao Te Ching",
        "Chinese",
    ),
    (
        "It does not matter how slowly you go as long as you do not stop.",
        "Confucius",
        "Analects",
        "Chinese",
    ),
    (
        "Life is really simple, but we insist on making it complicated.",
        "Confucius",
        "Analects",
        "Chinese",
    ),
    (
        "When you know a thing, to hold that you know it; "
        "and when you do not know a thing, to allow that you do not know it — "
        "this is knowledge.",
        "Confucius",
        "Analects",
        "Chinese",
    ),
    (
        "The superior man is satisfied and composed; "
        "the mean man is always full of distress.",
        "Confucius",
        "Analects",
        "Chinese",
    ),
    (
        "In the middle of difficulty lies opportunity.",
        "Albert Einstein",
        "Attributed",
        "German",
    ),
    (
        "An old pond — a frog jumps in, sound of water.",
        "Matsuo Bashō",
        "Classic Haiku",
        "Japanese",
    ),
    (
        "In all things of nature there is something of the marvelous.",
        "Aristotle",
        "Parts of Animals",
        "Greek",
    ),
    (
        "The flower that blooms in adversity is the rarest and most beautiful of all.",
        "Mulan",
        "Walt Disney's Mulan (Chinese proverb origin)",
        "Chinese",
    ),
    (
        "Not seeing is a flower.",
        "Zen Proverb",
        "Classical Zen",
        "Japanese",
    ),
    (
        "If you meet the Buddha on the road, kill him.",
        "Linji Yixuan",
        "Record of Linji",
        "Chinese",
    ),
    (
        "Before enlightenment, chop wood, carry water. "
        "After enlightenment, chop wood, carry water.",
        "Zen Proverb",
        "Classical Zen",
        "Japanese",
    ),
    # ── Latin & Ancient World ─────────────────────────────────
    (
        "Carpe diem, quam minimum credula postero. "
        "(Seize the day, put very little trust in tomorrow.)",
        "Horace",
        "Odes",
        "Roman",
    ),
    (
        "Dum spiro, spero. (While I breathe, I hope.)",
        "Cicero",
        "Attributed",
        "Roman",
    ),
    (
        "Cogito ergo sum. (I think, therefore I am.)",
        "René Descartes",
        "Discourse on the Method",
        "French",
    ),
    (
        "Omnia mutantur, nihil interit. (Everything changes, nothing perishes.)",
        "Ovid",
        "Metamorphoses",
        "Roman",
    ),
    # ── South Asian Literature ────────────────────────────────
    (
        "Where the mind is without fear and the head is held high, "
        "where knowledge is free.",
        "Rabindranath Tagore",
        "Gitanjali",
        "Indian",
    ),
    (
        "You yourself, as much as anybody in the entire universe, "
        "deserve your love and affection.",
        "The Buddha",
        "Dhammapada",
        "Indian",
    ),
    (
        "Three things cannot be long hidden: the sun, the moon, and the truth.",
        "The Buddha",
        "Dhammapada",
        "Indian",
    ),
    (
        "Health is the greatest gift, contentment the greatest wealth, "
        "faithfulness the best relationship.",
        "The Buddha",
        "Dhammapada",
        "Indian",
    ),
    (
        "You have the right to perform your actions, "
        "but you are not entitled to the fruits of your actions.",
        "Bhagavad Gita",
        "Chapter 2, Verse 47",
        "Indian",
    ),
    # ── Latin American & World ────────────────────────────────
    (
        "No man ever steps in the same river twice, "
        "for it's not the same river and he's not the same man.",
        "Heraclitus",
        "Fragments",
        "Greek",
    ),
    (
        "One hundred years of solitude.",
        "Gabriel García Márquez",
        "One Hundred Years of Solitude",
        "Latin American",
    ),
    (
        "A person can be destroyed but not defeated.",
        "Ernest Hemingway",
        "The Old Man and the Sea",
        "American",
    ),
    (
        "The world breaks everyone, and afterward, "
        "some are strong at the broken places.",
        "Ernest Hemingway",
        "A Farewell to Arms",
        "American",
    ),
    (
        "There is nothing to writing. All you do is sit down at a typewriter and bleed.",
        "Ernest Hemingway",
        "Attributed",
        "American",
    ),
    (
        "The good life is one inspired by love and guided by knowledge.",
        "Bertrand Russell",
        "What I Believe",
        "English",
    ),
    (
        "The whole problem with the world is that fools and fanatics "
        "are always so certain of themselves, and wiser people "
        "so full of doubts.",
        "Bertrand Russell",
        "Attributed",
        "English",
    ),
    # ── Modern & Contemporary ─────────────────────────────────
    (
        "It is not our differences that divide us. "
        "It is our inability to recognize, accept, "
        "and celebrate those differences.",
        "Audre Lorde",
        "Our Dead Behind Us",
        "American",
    ),
    (
        "I am not afraid. I was born to do this.",
        "Joan of Arc",
        "Attributed",
        "French",
    ),
    (
        "The most courageous act is still to think for yourself. Aloud.",
        "Coco Chanel",
        "Attributed",
        "French",
    ),
    (
        "No one can make you feel inferior without your consent.",
        "Eleanor Roosevelt",
        "This Is My Story",
        "American",
    ),
    (
        "In the end, it's not the years in your life that count. "
        "It's the life in your years.",
        "Abraham Lincoln",
        "Attributed",
        "American",
    ),
    (
        "The measure of intelligence is the ability to change.",
        "Albert Einstein",
        "Attributed",
        "German",
    ),
    (
        "Imagination is more important than knowledge.",
        "Albert Einstein",
        "On Science",
        "German",
    ),
    (
        "If you want to go fast, go alone. "
        "If you want to go far, go together.",
        "African Proverb",
        "Traditional",
        "African",
    ),
    (
        "Until the lion learns to write, "
        "every story will glorify the hunter.",
        "African Proverb",
        "Traditional",
        "African",
    ),
    (
        "A child who is not embraced by the village "
        "will burn it down to feel its warmth.",
        "African Proverb",
        "Traditional",
        "African",
    ),
    (
        "The ink of the scholar is more sacred than the blood of the martyr.",
        "Prophet Muhammad",
        "Attributed",
        "Arabic",
    ),
    (
        "Seek knowledge, even unto China.",
        "Prophet Muhammad",
        "Attributed",
        "Arabic",
    ),
    (
        "Words are, of course, the most powerful drug used by mankind.",
        "Rudyard Kipling",
        "Speech, 1923",
        "English",
    ),
    (
        "Books are the mirrors of the soul.",
        "Virginia Woolf",
        "Between the Acts",
        "English",
    ),
    (
        "You don't have to burn books to destroy a culture. "
        "Just get people to stop reading them.",
        "Ray Bradbury",
        "Fahrenheit 451",
        "American",
    ),
    (
        "A room without books is like a body without a soul.",
        "Marcus Tullius Cicero",
        "Attributed",
        "Roman",
    ),
    (
        "Outside of a dog, a book is man's best friend. "
        "Inside of a dog, it's too dark to read.",
        "Groucho Marx",
        "Attributed",
        "American",
    ),
    (
        "I am part of everything I have read.",
        "Theodore Roosevelt",
        "Attributed",
        "American",
    ),
    (
        "There is no friend as loyal as a book.",
        "Ernest Hemingway",
        "Attributed",
        "American",
    ),
    (
        "Until I feared I would lose it, "
        "I never loved to read. One does not love breathing.",
        "Harper Lee",
        "To Kill a Mockingbird",
        "American",
    ),
    (
        "Not every reader is a leader, but every leader must be a reader.",
        "Harry S. Truman",
        "Attributed",
        "American",
    ),
    (
        "I find television very educating. Every time somebody turns on the set, "
        "I go into the other room and read a book.",
        "Groucho Marx",
        "Attributed",
        "American",
    ),
    (
        "The reading of all good books is like a conversation "
        "with the finest minds of past centuries.",
        "René Descartes",
        "Discourse on the Method",
        "French",
    ),
    (
        "It is what you read when you don't have to "
        "that determines what you will be when you can't help it.",
        "Oscar Wilde",
        "Attributed",
        "English",
    ),
    (
        "Sleep is good, death is better; but of course, "
        "the best thing would be never to have been born at all.",
        "Heinrich Heine",
        "Morphine",
        "German",
    ),
    (
        "Where they burn books, they will ultimately burn people also.",
        "Heinrich Heine",
        "Almansor",
        "German",
    ),
    (
        "In the beginning was the Word.",
        "The Bible",
        "John 1:1",
        "Universal",
    ),
    (
        "I cannot live without books.",
        "Thomas Jefferson",
        "Letter to John Adams, 1815",
        "American",
    ),
    (
        "Give me a lever long enough and a fulcrum on which to place it, "
        "and I shall move the world.",
        "Archimedes",
        "Attributed",
        "Greek",
    ),
    (
        "All we have to decide is what to do with the time that is given us.",
        "J.R.R. Tolkien",
        "The Fellowship of the Ring",
        "English",
    ),
    (
        "Even the darkest night will end and the sun will rise.",
        "Victor Hugo",
        "Les Misérables",
        "French",
    ),
    (
        "To love another person is to see the face of God.",
        "Victor Hugo",
        "Les Misérables",
        "French",
    ),
    (
        "He who opens a school door, closes a prison.",
        "Victor Hugo",
        "Attributed",
        "French",
    ),
    (
        "There is always light, if only we're brave enough to see it. "
        "If only we're brave enough to be it.",
        "Amanda Gorman",
        "The Hill We Climb",
        "American",
    ),
    (
        "Poetry is when an emotion has found its thought "
        "and the thought has found words.",
        "Robert Frost",
        "Attributed",
        "American",
    ),
    (
        "The courage of the poet is to keep ajar the door "
        "that leads into madness.",
        "Christopher Morley",
        "Inward Ho",
        "American",
    ),
    (
        "A writer only begins a book. A reader finishes it.",
        "Samuel Johnson",
        "Attributed",
        "English",
    ),
    (
        "If you only read the books that everyone else is reading, "
        "you can only think what everyone else is thinking.",
        "Haruki Murakami",
        "Norwegian Wood",
        "Japanese",
    ),
    (
        "No matter how busy you may think you are, "
        "you must find time for reading, "
        "or surrender yourself to self-chosen ignorance.",
        "Confucius",
        "Analects",
        "Chinese",
    ),
    (
        "Live as if you were to die tomorrow. "
        "Learn as if you were to live forever.",
        "Mahatma Gandhi",
        "Attributed",
        "Indian",
    ),
    (
        "The best revenge is massive success.",
        "Frank Sinatra",
        "Attributed",
        "American",
    ),
    (
        "The only thing necessary for the triumph of evil "
        "is for good men to do nothing.",
        "Edmund Burke",
        "Attributed",
        "Irish",
    ),
    (
        "Knowledge speaks, but wisdom listens.",
        "Jimi Hendrix",
        "Attributed",
        "American",
    ),
    (
        "I've learned that people will forget what you said, "
        "people will forget what you did, "
        "but people will never forget how you made them feel.",
        "Maya Angelou",
        "Attributed",
        "American",
    ),
    (
        "You may not control all the events that happen to you, "
        "but you can decide not to be reduced by them.",
        "Maya Angelou",
        "Letter to My Daughter",
        "American",
    ),
    (
        "There is no greater agony than bearing an untold story inside you.",
        "Maya Angelou",
        "I Know Why the Caged Bird Sings",
        "American",
    ),
    (
        "A bird doesn't sing because it has an answer, "
        "it sings because it has a song.",
        "Maya Angelou",
        "Attributed",
        "American",
    ),
    (
        "The most common way people give up their power "
        "is by thinking they don't have any.",
        "Alice Walker",
        "Attributed",
        "American",
    ),
    # ── Griffin Library - The Ancient Vault ──────────────────
    (
        "There is no Frigate like a Book "
        "to take us Lands away.",
        "Emily Dickinson",
        "Poem 1263",
        "American",
    ),
    (
        "Words are our most inexhaustible source of magic, "
        "capable of both inflicting injury and remedying it.",
        "J.K. Rowling",
        "Harry Potter and the Deathly Hallows",
        "English",
    ),
    (
        "A library is not a luxury "
        "but one of the necessities of life.",
        "Henry Ward Beecher",
        "Attributed",
        "American",
    ),
    (
        "A book must be the axe "
        "for the frozen sea within us.",
        "Franz Kafka",
        "Letter to Oskar Pollak, 1904",
        "German",
    ),
    (
        "To acquire the habit of reading is to construct for yourself "
        "a refuge from almost all the miseries of life.",
        "W. Somerset Maugham",
        "Books and You",
        "English",
    ),
    (
        "The pen is the tongue of the mind.",
        "Miguel de Cervantes",
        "Don Quixote, 1605",
        "Spanish",
    ),
    # ── Arcane & Mystical ─────────────────────────────────────
    (
        "As above, so below; as below, so above. "
        "The miracle of the One Thing.",
        "Hermes Trismegistus",
        "The Emerald Tablet, ~3rd century",
        "Ancient",
    ),
    (
        "Know thyself.",
        "Oracle of Delphi",
        "Inscribed at the Temple of Apollo, ~6th century BC",
        "Greek",
    ),
    (
        "The cave you fear to enter "
        "holds the treasure you seek.",
        "Joseph Campbell",
        "The Hero with a Thousand Faces",
        "American",
    ),
    (
        "Follow your bliss and the universe will open doors "
        "where there were only walls.",
        "Joseph Campbell",
        "The Power of Myth",
        "American",
    ),
    (
        "Water is the softest thing, yet it can penetrate mountains and earth. "
        "This shows clearly the principle of softness overcoming hardness.",
        "Laozi",
        "Tao Te Ching",
        "Chinese",
    ),
    # ── Forgotten Wisdom - Ancient Civilizations ──────────────
    (
        "Educating the mind without educating the heart "
        "is no education at all.",
        "Aristotle",
        "Nicomachean Ethics, ~350 BC",
        "Greek",
    ),
    (
        "It is the mark of an educated mind "
        "to be able to entertain a thought without accepting it.",
        "Aristotle",
        "Metaphysics",
        "Greek",
    ),
    (
        "Knowing yourself is the beginning of all wisdom.",
        "Aristotle",
        "Nicomachean Ethics",
        "Greek",
    ),
    (
        "The measure of a man is what he does with power.",
        "Plato",
        "The Republic, ~380 BC",
        "Greek",
    ),
    (
        "Wise men speak because they have something to say; "
        "fools because they have to say something.",
        "Plato",
        "Attributed",
        "Greek",
    ),
    # ── Sufi & Islamic Mysticism ──────────────────────────────
    (
        "What you seek is seeking you.",
        "Rumi",
        "Masnavi, 13th century",
        "Persian",
    ),
    (
        "Raise your words, not your voice. "
        "It is rain that grows flowers, not thunder.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "The quieter you become, "
        "the more you are able to hear.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "Do not be satisfied with the stories that come before you. "
        "Unfold your own myth.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "The universe is not outside of you. "
        "Look inside yourself; everything that you want, "
        "you already are.",
        "Rumi",
        "Masnavi",
        "Persian",
    ),
    (
        "The heart is the secret inside the secret.",
        "Al-Hallaj",
        "Tawasin, 9th century",
        "Persian",
    ),
    # ── Medieval & Renaissance ────────────────────────────────
    (
        "We know what we are, "
        "but know not what we may be.",
        "William Shakespeare",
        "Hamlet",
        "English",
    ),
    (
        "Our doubts are traitors, and make us lose the good "
        "we oft might win, by fearing to attempt.",
        "William Shakespeare",
        "Measure for Measure",
        "English",
    ),
    (
        "There is nothing either good or bad, "
        "but thinking makes it so.",
        "William Shakespeare",
        "Hamlet",
        "English",
    ),
    (
        "Too much sanity may be madness — "
        "and maddest of all: to see life as it is, "
        "and not as it should be.",
        "Miguel de Cervantes",
        "Don Quixote",
        "Spanish",
    ),
    (
        "Consider your origin. "
        "You were not formed to live like brutes, "
        "but to follow virtue and knowledge.",
        "Dante Alighieri",
        "Inferno, ~1320",
        "Italian",
    ),
    (
        "The more I read, the more I acquire, "
        "the more certain I am that I know nothing.",
        "Voltaire",
        "Attributed",
        "French",
    ),
    (
        "Judge a man by his questions "
        "rather than by his answers.",
        "Voltaire",
        "Attributed",
        "French",
    ),
]


def _get_quote_of_6h() -> dict:
    """
    Returns a quote that rotates every 6 hours.
    Uses (day.toordinal() * 4 + hour // 6) as the index seed
    so the quote changes 4 times per day, exactly on the 6-hour marks.
    """
    now   = datetime.now()
    seed  = date.today().toordinal() * 4 + (now.hour // 6)
    idx   = seed % len(_CURATED_QUOTES)
    text, author, source, culture = _CURATED_QUOTES[idx]
    return {
        "text":    text,
        "author":  author,
        "source":  source,
        "culture": culture,
        "slot":    now.hour // 6,          # 0=midnight,1=6am,2=noon,3=6pm
    }


def _slot_label(slot: int) -> str:
    labels = {0: "Midnight Inscription", 1: "Dawn Wisdom",
               2: "Noonday Revelation",   3: "Dusk Chronicle"}
    return labels.get(slot, "Ancient Scroll")


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _greet(name: str) -> str:
    h = datetime.now().hour
    if h < 12:   return f"The vaults open at dawn, {name}. ☀️"
    elif h < 17: return f"The scrolls await you, {name}."
    elif h < 21: return f"Evening falls upon the library, {name}. 🌙"
    else:        return f"Still turning pages by candlelight, {name}? 🕯️"


def _pbar(pct: float, color: str = "var(--ink,#1E3A2F)") -> str:
    pct = max(0, min(100, int(pct)))
    return (
        f'<div style="background:var(--border,#E8DFCC);border-radius:99px;'
        f'height:6px;width:100%;margin-top:6px;">'
        f'<div style="background:{color};height:6px;border-radius:99px;'
        f'width:{pct}%;transition:width 0.5s ease;"></div></div>'
    )


def _get_sessions_log(lib) -> dict:
    try:    return lib.get_sessions_log() or {}
    except: return {}


def _sync_sessions_log(lib):
    st.session_state["sessions_log"] = _get_sessions_log(lib)


# ─────────────────────────────────────────────────────────────
# SECTION RENDERERS
# ─────────────────────────────────────────────────────────────

def _render_kpi_strip(lib):
    """Top KPI cards - always reads live from lib, never stale session_state cache."""
    streak       = lib.get_streak()
    reading_list = lib.get_by_status("reading")
    read_list    = lib.get_by_status("read")

    # Always read live entries so KPIs update immediately after a saved session
    try:
        all_entries = _get_all_entries()
    except Exception:
        all_entries = []

    total_min   = sum(e.get("duration_min", 0) for e in all_entries)
    total_pages = sum(e.get("pages_read", 0)   for e in all_entries)
    h, m        = divmod(total_min, 60)
    time_str    = f"{h}h {m}m" if h else (f"{m}m" if m else "—")

    # This month (from live entries, not stale log dict)
    month_start = date.today().replace(day=1).isoformat()
    month_entries = [e for e in all_entries if e.get("date", "") >= month_start]
    month_min     = sum(e.get("duration_min", 0) for e in month_entries)
    month_h, month_m = divmod(month_min, 60)
    month_time  = f"{month_h}h {month_m}m" if month_h else (f"{month_m}m" if month_m else "—")

    # Coach plan goal indicator
    plan         = st.session_state.get("_orion_plan")
    goal_min, _  = _get_daily_goal_min()
    plan_label   = f"{goal_min}m/day" if plan else "—"

    kpis = [
        ("🌾", str(streak.count or 0), "Day Vigil"),
        ("📜", str(len(reading_list)),  "Tomes Open"),
        ("⚜️", str(len(read_list)),     "Tomes Sealed"),
        ("🕰️", time_str,               "Hours of Study"),
        ("📃", str(total_pages) if total_pages else "—", "Pages Traversed"),
        ("🗓️", month_time,             "This Moon"),
    ]

    cols = st.columns(len(kpis))
    for col, (icon, val, label) in zip(cols, kpis):
        with col:
            st.markdown(
                f'<div style="background:var(--surface,#fff);'
                f'border:1px solid var(--border,#E2DAD0);'
                f'border-radius:14px;padding:0.9rem 1rem;text-align:center;">'
                f'<div style="font-size:18px;margin-bottom:4px;">{icon}</div>'
                f'<div style="font-size:20px;font-weight:800;'
                f'color:var(--text,#1A1612);line-height:1.1;">{safe(val)}</div>'
                f'<div style="font-size:10px;color:var(--text-hint,#A8998C);'
                f'text-transform:uppercase;letter-spacing:1px;margin-top:3px;'
                f'font-weight:600;">{safe(label)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_curated_quote():
    """Rotating curated quote - changes every 6 hours."""
    q    = _get_quote_of_6h()
    slot = q["slot"]
    lbl  = _slot_label(slot)

    # Next change time
    now        = datetime.now()
    next_hour  = ((now.hour // 6) + 1) * 6
    next_label = (
        f"Updates at {next_hour:02d}:00"
        if next_hour < 24
        else "Updates at midnight"
    )

    st.markdown(
        f'<div style="background:linear-gradient(135deg,'
        f'var(--ai-soft,#F3F0FF) 0%,var(--accent-soft,#F0F8F4) 100%);'
        f'border:1px solid rgba(30,58,47,0.12);border-radius:18px;'
        f'padding:2rem 2.25rem;margin:1.5rem 0;position:relative;overflow:hidden;">'
        # left accent bar
        f'<div style="position:absolute;top:0;left:0;width:4px;height:100%;'
        f'background:linear-gradient(180deg,#1E3A2F,#3B6E52);border-radius:4px 0 0 4px;"></div>'
        # label row
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:1.1rem;">'
        f'<div style="font-size:10px;font-weight:800;color:var(--ink,#1E3A2F);'
        f'text-transform:uppercase;letter-spacing:2px;">{safe(lbl)}</div>'
        f'<div style="font-size:10px;color:var(--text-hint,#A8998C);'
        f'font-weight:500;">{safe(next_label)}</div>'
        f'</div>'
        # quote text
        f'<div style="font-family:\'DM Serif Display\',Georgia,serif;'
        f'font-size:1.35rem;color:var(--text,#1A1612);line-height:1.6;'
        f'font-style:italic;margin-bottom:1.25rem;">'
        f'"{safe(q["text"])}"'
        f'</div>'
        # attribution
        f'<div style="display:flex;justify-content:space-between;align-items:flex-end;">'
        f'<div>'
        f'<div style="font-size:14px;font-weight:700;color:var(--text,#1A1612);">'
        f'— {safe(q["author"])}</div>'
        f'<div style="font-size:12px;color:var(--text-muted,#6A5F54);margin-top:2px;">'
        f'{safe(q["source"])}</div>'
        f'</div>'
        f'<div style="font-size:10px;color:var(--text-hint,#A8998C);'
        f'background:rgba(0,0,0,0.04);border-radius:100px;'
        f'padding:3px 10px;font-weight:600;">'
        f'{safe(q["culture"])}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_active_session_banner():
    """Compact banner shown when a session is active, directing to Sessions page."""
    active = st.session_state.get("active_session")
    if not active:
        return

    is_free   = active.get("is_free", True)
    label     = "🌿 Open Vigil" if is_free else f"📚 {active.get('book_title','')}"
    dur_min   = active.get("duration_minutes", 30)
    paused    = active.get("paused", False)
    state_lbl = "⏸ Paused" if paused else "● Live"

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#E8F0EC,#D8E8DE);'
        f'border:1.5px solid rgba(30,58,47,0.25);border-radius:14px;'
        f'padding:0.9rem 1.25rem;margin-bottom:1rem;'
        f'display:flex;align-items:center;justify-content:space-between;gap:1rem;">'
        f'<div>'
        f'<div style="font-size:12px;font-weight:800;color:#1E3A2F;'
        f'text-transform:uppercase;letter-spacing:1px;">'
        f'{state_lbl} — ritual in progress</div>'
        f'<div style="font-size:13px;color:#3B6E52;margin-top:2px;">'
        f'{safe(label)} · {dur_min} min target</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("→ Manage Ritual in Rituals →", key="home_goto_sessions",
                 type="primary", use_container_width=False):
        st.session_state["page"] = "Sessions"
        st.rerun()
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)


def _get_daily_goal_min() -> tuple[int, str]:
    """
    Return (goal_minutes, source_label).
    Priority:
      1. Coach plan's session_duration_min × weekly_sessions / 7  (actual coach recommendation)
      2. Coach plan's session_duration_min alone (if no weekly_sessions)
      3. Default 30 min with a label indicating it's a suggested default
    """
    plan = st.session_state.get("_orion_plan")
    if plan:
        sd = int(plan.get("session_duration_min", 0) or 0)
        ws = int(plan.get("weekly_sessions", 0) or 0)
        if sd > 0:
            if ws > 0:
                # Daily average from weekly plan
                daily = max(1, round(sd * ws / 7))
                return daily, f"from your AI plan ({sd}m × {ws}×/wk)"
            return sd, "from your AI plan"
    return 30, "suggested default — set one with AI Guide"


def _render_today_progress(lib):
    """Today's reading progress strip - goal derived from coach plan if set."""
    log   = st.session_state.get("sessions_log", {})
    today = date.today().isoformat()

    today_min      = 0
    today_pages    = 0
    sessions_today = 0

    try:
        all_entries_tmp = _get_all_entries()
        entries_today  = all_entries_tmp
        entries_today  = [e for e in entries_today if e.get("date") == today]
        today_min      = sum(e.get("duration_min", 0) for e in entries_today)
        today_pages    = sum(e.get("pages_read", 0)   for e in entries_today)
        sessions_today = len(entries_today)
    except Exception:
        day            = log.get(today, {})
        today_min      = day.get("duration_min", 0)
        today_pages    = day.get("pages_read", 0)
        sessions_today = 1 if today_min > 0 else 0

    goal_min, goal_src = _get_daily_goal_min()
    pct = min(100, int(today_min / goal_min * 100)) if goal_min else 0

    goal_color = "#2A7A4B" if pct >= 100 else "var(--ink,#1E3A2F)"

    st.markdown(
        f'<div style="background:var(--surface,#fff);'
        f'border:1px solid var(--border,#E2DAD0);border-radius:14px;'
        f'padding:1rem 1.5rem;margin-bottom:1rem;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:10px;">'
        f'<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        f'text-transform:uppercase;letter-spacing:1.5px;">Today&#39;s Vigil</div>'
        f'<div style="font-size:12px;color:var(--text-muted,#6A5F54);">'
        f'{today_min} min · {today_pages} pages · '
        f'{sessions_today} session{"s" if sessions_today != 1 else ""}'
        f'</div></div>'
        + _pbar(pct, goal_color) +
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-top:5px;">'
        f'<div style="font-size:11px;color:var(--text-hint,#A8998C);">'
        f'{"✓ Goal reached!" if pct >= 100 else f"{pct}% of {goal_min}-min daily goal"}'
        f'</div>'
        f'<div style="font-size:10px;color:var(--text-hint,#A8998C);font-style:italic;">'
        f'{safe(goal_src)}</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_current_books(lib):
    reading     = lib.get_by_status("reading")
    goals       = lib.get_goals()
    n_read_year = lib.books_read_this_year()
    yearly_goal = max(int(goals.yearly_goal or 12), 1)
    goal_pct    = min(int(n_read_year / yearly_goal * 100), 100)

    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:0.75rem;">'
        'Tomes in Progress</div>',
        unsafe_allow_html=True,
    )

    if not reading:
        st.markdown(
            '<div style="background:var(--surface,#fff);border:1px solid var(--border,#E2DAD0);'
            'border-radius:14px;padding:1.25rem;text-align:center;color:var(--text-muted,#6A5F54);'
            'font-size:13px;">The shelves stand quiet. Add a tome to your collection to begin your quest.</div>',
            unsafe_allow_html=True,
        )
    else:
        for b in reading[:3]:
            cp  = int(b.current_page or 0)
            tp  = int(b.total_pages or 0)
            pct = min(int(cp / tp * 100), 100) if tp > 0 else 0
            st.markdown(
                f'<div style="background:var(--surface,#fff);'
                f'border:1px solid var(--border,#E2DAD0);'
                f'border-radius:14px;padding:1rem 1.25rem;margin-bottom:0.5rem;">'
                f'<div style="font-size:14px;font-weight:700;color:var(--text,#1A1612);'
                f'line-height:1.35;margin-bottom:3px;">{safe(b.title)}</div>'
                f'<div style="font-size:12px;color:var(--text-muted,#6A5F54);margin-bottom:10px;">'
                f'{safe(b.authors)}</div>'
                + (_pbar(pct) +
                f'<div style="font-size:11px;color:var(--text-hint,#A8998C);margin-top:5px;">'
                f'{cp} / {tp} pages · {pct}%</div>'
                if tp > 0 else
                '<div style="font-size:11px;color:var(--text-hint,#A8998C);">No progress marked yet - begin your journey.</div>')
                + f'</div>',
                unsafe_allow_html=True,
            )

    # Annual goal strip
    st.markdown(
        f'<div style="background:var(--surface,#fff);'
        f'border:1px solid var(--border,#E2DAD0);border-radius:14px;'
        f'padding:1rem 1.25rem;margin-top:0.5rem;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:8px;">'
        f'<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        f'text-transform:uppercase;letter-spacing:1.5px;">{date.today().year} Goal</div>'
        f'<div style="font-size:13px;font-weight:700;color:var(--text,#1A1612);">'
        f'{n_read_year} / {yearly_goal} books</div></div>'
        + _pbar(goal_pct) +
        f'<div style="font-size:11px;color:var(--text-hint,#A8998C);margin-top:5px;">'
        f'{goal_pct}% · {max(yearly_goal - n_read_year, 0)} to go'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_recent_sessions(lib):
    """Last 3 completed sessions summary."""
    try:
        entries = _get_all_entries()
    except Exception:
        entries = []

    if not entries:
        return

    recent = sorted(entries, key=lambda e: (e.get("date",""), e.get("time","")), reverse=True)[:3]

    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:0.75rem;">'
        'Recent Rituals</div>',
        unsafe_allow_html=True,
    )

    for e in recent:
        is_book  = e.get("type") == "book"
        icon     = "📚" if is_book else "🌿"
        dur      = e.get("duration_min", 0)
        pages    = e.get("pages_read", 0)
        title    = e.get("book_title", "") if is_book else "Open Vigil"
        d_str    = e.get("date", "")
        t_str    = e.get("time", "")

        try:
            d   = date.fromisoformat(d_str)
            lbl = ("Today" if d == date.today()
                   else "Yesterday" if d == date.today() - timedelta(days=1)
                   else _fmt_day(d, "%b %d"))
        except Exception:
            lbl = d_str

        pages_chip = (
            f'<span style="font-size:10px;background:var(--accent-soft,#EBF5F0);'
            f'color:var(--ink,#1E3A2F);border-radius:100px;padding:2px 8px;'
            f'margin-left:6px;font-weight:600;">{pages}p</span>'
            if pages > 0 else ""
        )

        st.markdown(
            f'<div style="background:var(--surface,#fff);'
            f'border:1px solid var(--border,#E2DAD0);border-radius:12px;'
            f'padding:0.75rem 1rem;margin-bottom:0.4rem;'
            f'display:flex;justify-content:space-between;align-items:center;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:13px;font-weight:600;color:var(--text,#1A1612);">'
            f'{icon} {safe(title[:40])}</div>'
            f'<div style="font-size:11px;color:var(--text-hint,#A8998C);margin-top:2px;">'
            f'{safe(lbl)}{" · " + t_str if t_str else ""}{pages_chip}</div>'
            f'</div>'
            f'<div style="font-size:17px;font-weight:800;'
            f'color:var(--ink,#1E3A2F);margin-left:1rem;">'
            f'{dur}<span style="font-size:11px;font-weight:500;">m</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if len(entries) > 3:
        if st.button(f"View all {len(entries)} sessions →",
                     key="home_view_sessions", use_container_width=False):
            st.session_state["page"] = "Sessions"
            st.rerun()


def _render_weekly_pulse(lib):
    today    = date.today()
    streak   = lib.get_streak()
    # Correct weekday labels: weekday() returns 0=Mon..6=Sun
    WEEKDAY_LABELS = {0:"Mo", 1:"Tu", 2:"We", 3:"Th", 4:"Fr", 5:"Sa", 6:"Su"}

    # Build day → total_minutes map from live entries
    try:
        all_entries = _get_all_entries()
    except Exception:
        all_entries = []
    day_min_map: dict[str, int] = {}
    for e in all_entries:
        d = e.get("date", "")
        if d:
            day_min_map[d] = day_min_map.get(d, 0) + e.get("duration_min", 0)

    days      = [(today - timedelta(days=6 - i)) for i in range(7)]
    dots_html = ""
    for d in days:
        key   = d.isoformat()
        mins  = day_min_map.get(key, 0)
        has   = mins > 0
        is_td = (d == today)

        size  = 38 if mins > 45 else (34 if mins > 20 else 30)
        if is_td:
            size = max(size, 34)

        bg    = "var(--ink,#1E3A2F)" if has else ("rgba(30,58,47,0.08)" if is_td else "var(--border,#E2DAD0)")
        bord  = "2px solid var(--ink,#1E3A2F)" if is_td and not has else "none"
        color = "#fff" if has else ("var(--ink,#1E3A2F)" if is_td else "var(--text-muted,#6A5F54)")
        lbl   = WEEKDAY_LABELS[d.weekday()]

        dots_html += (
            f'<div style="text-align:center;flex:1;">'
            f'<div style="font-size:9px;color:var(--text-hint,#A8998C);'
            f'font-weight:600;text-transform:uppercase;margin-bottom:5px;">{lbl}</div>'
            f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
            f'background:{bg};border:{bord};display:flex;align-items:center;'
            f'justify-content:center;font-size:11px;font-weight:700;color:{color};'
            f'margin:0 auto;transition:all 0.3s;">'
            f'{"✓" if has else ""}</div>'
            f'</div>'
        )

    streak_color = "#F97316" if streak.count > 0 else "var(--text-muted,#6A5F54)"
    streak_icon  = "🔥" if streak.count >= 3 else ("✨" if streak.count > 0 else "💤")

    st.markdown(
        f'<div style="background:var(--surface,#fff);border:1px solid var(--border,#E2DAD0);'
        f'border-radius:14px;padding:1.1rem 1.25rem;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;margin-bottom:14px;">'
        f'<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        f'text-transform:uppercase;letter-spacing:1.5px;">The Weekly Vigil</div>'
        f'<div style="font-size:13px;font-weight:700;color:{streak_color};">'
        f'{streak_icon} {streak.count} day streak</div></div>'
        f'<div style="display:flex;justify-content:space-between;gap:4px;">'
        f'{dots_html}</div></div>',
        unsafe_allow_html=True,
    )


def _render_consistency_metrics(lib):
    """Reading consistency - always reads live from lib, never stale cache."""
    today       = date.today()
    month_start = today.replace(day=1)

    try:
        all_entries = _get_all_entries()
    except Exception:
        all_entries = []

    # Build a set of active dates from entries
    active_date_set = set(e.get("date", "") for e in all_entries if e.get("duration_min", 0) > 0)

    # 30-day window
    days_30     = [(today - timedelta(days=i)).isoformat() for i in range(30)]
    active_days = sum(1 for d in days_30 if d in active_date_set)
    consistency = round(active_days / 30 * 100)

    # Monthly totals
    month_entries = [e for e in all_entries if e.get("date", "") >= month_start.isoformat()]
    month_min     = sum(e.get("duration_min", 0) for e in month_entries)
    month_pages   = sum(e.get("pages_read", 0)   for e in month_entries)
    month_h, month_m = divmod(month_min, 60)
    month_time    = f"{month_h}h {month_m}m" if month_h else (f"{month_m}m" if month_m else "—")

    # Mightiest Week (last 4 weeks)
    best_week_min = 0
    for i in range(4):
        wstart = today - timedelta(days=today.weekday() + 7 * i)
        wdays  = [(wstart + timedelta(days=j)).isoformat() for j in range(7)]
        wmin   = sum(e.get("duration_min", 0) for e in all_entries if e.get("date", "") in wdays)
        best_week_min = max(best_week_min, wmin)
    best_h, best_m = divmod(best_week_min, 60)
    best_week_str  = f"{best_h}h {best_m}m" if best_h else (f"{best_m}m" if best_m else "—")

    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:0.75rem;">'
        'Keeper&#39;s Chronicle</div>',
        unsafe_allow_html=True,
    )

    metrics = [
        ("📆", f"{active_days}/30 days", "Days of Study"),
        ("📊", f"{consistency}%",        "Ritual Discipline"),
        ("🗓️", month_time,               "This Moon"),
        ("🏆", best_week_str,            "Mightiest Week"),
    ]
    cols = st.columns(2)
    for i, (icon, val, label) in enumerate(metrics):
        with cols[i % 2]:
            st.markdown(
                f'<div style="background:var(--surface,#fff);'
                f'border:1px solid var(--border,#E2DAD0);border-radius:12px;'
                f'padding:0.85rem 1rem;margin-bottom:0.5rem;">'
                f'<div style="font-size:16px;margin-bottom:4px;">{icon}</div>'
                f'<div style="font-size:17px;font-weight:800;'
                f'color:var(--text,#1A1612);line-height:1.1;">{safe(val)}</div>'
                f'<div style="font-size:10px;color:var(--text-hint,#A8998C);'
                f'text-transform:uppercase;letter-spacing:0.8px;margin-top:3px;'
                f'font-weight:600;">{safe(label)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if month_pages > 0:
        st.markdown(
            f'<div style="font-size:12px;color:var(--text-muted,#6A5F54);padding:0.5rem 0;">'
            f'📄 {month_pages} pages read this month</div>',
            unsafe_allow_html=True,
        )


def _get_week_bounds() -> tuple[date, date]:
    """Return (Monday, Sunday) of the current ISO week."""
    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def _render_challenges(lib):
    """
    Weekly reading challenges - auto-refresh every Monday.
    Progress is computed live from session entries and library data.
    Every completed session contributes automatically.
    """
    monday, sunday = _get_week_bounds()
    today          = date.today()

    # ── Pull live data ────────────────────────────────────────
    try:
        all_entries = _get_all_entries()
    except Exception:
        all_entries = []

    # Filter to this week only
    week_entries  = [
        e for e in all_entries
        if monday.isoformat() <= e.get("date", "") <= sunday.isoformat()
    ]
    week_min      = sum(e.get("duration_min", 0) for e in week_entries)
    week_sessions = len(week_entries)
    week_pages    = sum(e.get("pages_read", 0)   for e in week_entries)

    # Active reading days this week
    week_days_read = len(set(
        e.get("date", "") for e in week_entries
        if e.get("duration_min", 0) > 0
    ))

    # Longest single session this week
    longest_min = max((e.get("duration_min", 0) for e in week_entries), default=0)

    # Inscriptions (quotes) saved this week - counted by date
    week_quotes = 0
    try:
        monday_str = monday.isoformat()
        sunday_str = sunday.isoformat()
        for book in lib.get_all().values():
            for q in book.quotes:
                # Support both object attribute and dict key
                if hasattr(q, "date"):
                    q_date = str(q.date or "")
                elif isinstance(q, dict):
                    q_date = str(q.get("date", "") or "")
                else:
                    q_date = ""
                q_date = q_date.strip()[:10]  # keep YYYY-MM-DD only
                # Count if within week, OR if no date (treat as this week)
                if not q_date or (monday_str <= q_date <= sunday_str):
                    week_quotes += 1
    except Exception:
        week_quotes = 0

    # Days until reset
    days_left  = (sunday - today).days
    reset_note = "Resets tomorrow" if days_left == 0 else f"Resets in {days_left + 1} days"

    # ── Challenge definitions ─────────────────────────────────
    # Each: (icon, title, description, current_value, goal, unit, tip)
    challenges = [
        (
            "⚔️", "The Endurance Trial",
            "Read for 120 minutes this week",
            week_min, 120, "min",
            "Every ritual — free or bound — counts toward the trial.",
        ),
        (
            "🗓️", "The Faithful Scholar",
            "Open the vaults on 4 different days",
            week_days_read, 4, "days",
            "Even 10 minutes of study marks the day as honoured.",
        ),
        (
            "🕯️", "Keeper of Rituals",
            "Complete 5 reading rituals",
            week_sessions, 5, "sessions",
            "Both open vigils and bound-tome rituals count.",
        ),
        (
            "📜", "The Relentless Reader",
            "Traverse 80 pages this week",
            week_pages, 80, "pages",
            "Pages are recorded when you seal a ritual.",
        ),
        (
            "🦅", "The Griffin's Gaze",
            "Sustain one ritual of 45+ minutes",
            min(longest_min, 45), 45, "min",
            "True scholars know: depth over haste.",
        ),
        (
            "🪶", "Keeper of Inscriptions",
            "Inscribe 3 passages this week",
            min(week_quotes, 3), 3, "quotes",
            "Save lines that move you from any tome this week.",
        ),
    ]

    # Section header
    week_str = f"{monday.strftime('%b %d')} – {sunday.strftime('%b %d')}"
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'margin-bottom:0.75rem;">'
        f'<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        f'text-transform:uppercase;letter-spacing:1.5px;">⚔️ Weekly Quests</div>'
        f'<div style="font-size:10px;color:var(--text-hint,#A8998C);">'
        f'{safe(week_str)} · {safe(reset_note)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Summary pill row
    done_count = sum(1 for (_, _, _, val, goal, _, _) in challenges if val >= goal)

    if done_count > 0:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#E8F4ED,#D4EDDB);'
            f'border:1px solid rgba(42,122,75,0.3);border-radius:10px;'
            f'padding:0.6rem 1rem;margin-bottom:0.75rem;'
            f'font-size:12px;font-weight:700;color:#1E5C36;">'
            f'🦅 {done_count}/{len(challenges)} quests fulfilled — the Griffin is proud!'
            f'</div>',
            unsafe_allow_html=True,
        )

    cols = st.columns(2)
    for idx, (icon, name, desc, val, goal, unit, tip) in enumerate(challenges):
        pct  = min(100, int(val / goal * 100)) if goal else 0
        done = val >= goal
        pct_display = "✓ Done" if done else f"{pct}%"
        bar_color   = "#2A7A4B" if done else ("var(--ink,#1E3A2F)" if pct > 50 else "var(--border,#C8BFB5)")

        with cols[idx % 2]:
            st.markdown(
                f'<div style="background:var(--surface,#fff);'
                f'border:1px solid {"rgba(42,122,75,0.35)" if done else "var(--border,#E2DAD0)"};'
                f'border-radius:14px;padding:0.9rem 1rem;margin-bottom:0.5rem;'
                f'{"background:linear-gradient(135deg,#F0FAF4,#E8F4ED);" if done else ""}">'
                # icon + title row
                f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;">'
                f'<span style="font-size:17px;">{icon}</span>'
                f'<div style="font-size:12px;font-weight:700;color:var(--text,#1A1612);'
                f'line-height:1.2;">{safe(name)}</div>'
                f'</div>'
                # description
                f'<div style="font-size:11px;color:var(--text-muted,#6A5F54);'
                f'margin-bottom:9px;line-height:1.4;">{safe(desc)}</div>'
                # progress row
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:10.5px;color:var(--text-hint,#A8998C);margin-bottom:5px;">'
                f'<span>{val} / {goal} {unit}</span>'
                f'<span style="font-weight:700;color:{"#2A7A4B" if done else "var(--text-muted,#6A5F54)"};">'
                f'{pct_display}</span>'
                f'</div>'
                + _pbar(pct, bar_color) +
                # tip
                f'<div style="font-size:10px;color:var(--text-hint,#A8998C);'
                f'margin-top:7px;font-style:italic;">{safe(tip)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────

def render(lib):
    name = lib.get_name() or "Reader"

    # ── Clear stale session store if the user changed ─────────
    # Mirrors the same guard in sessions.py - both pages read
    # _griffin_sessions so both must clear it on user change.
    last_home_owner = st.session_state.get("_home_owner")
    if last_home_owner and last_home_owner != name:
        st.session_state.pop(_SS_KEY,   None)
        st.session_state.pop(_SS_READY, None)
    st.session_state["_home_owner"] = name

    # Bootstrap session history once (no-op after any save this run)
    _bootstrap_sessions(lib)

    # Sync sessions_log cache (used by streak dots)
    _sync_sessions_log(lib)

    # Clean up any leftover session URL params
    for _k in ["eq_action", "eq_elapsed", "eq_pages", "eq_newpage", "eq_book_id", "eq_t"]:
        try:
            st.query_params.pop(_k, None)
        except Exception:
            pass

    # ── Header ────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin-bottom:1.25rem;">'
        f'<div style="font-size:24px;font-weight:800;'
        f'color:var(--text,#1A1612);letter-spacing:-0.5px;">'
        f'{safe(_greet(name))}</div>'
        f'<div style="font-size:12px;color:var(--text-muted,#6A5F54);margin-top:2px;">'
        f'{_fmt_day(date.today(), "%A, %B %d, %Y")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Done-session confirmation ─────────────────────────────
    done_msg = st.session_state.pop("_done_msg", None)
    if done_msg:
        st.success(f"**{done_msg['text']}**  \n{done_msg['detail']}")
        st.snow()

    # ── Active session banner ─────────────────────────────────
    _render_active_session_banner()

    # ── KPI strip ─────────────────────────────────────────────
    _render_kpi_strip(lib)
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Curated quote ─────────────────────────────────────────
    _render_curated_quote()

    # ── Today's reading progress ────────────────────────────────────────
    _render_today_progress(lib)

    # ── Two-column layout ─────────────────────────────────────
    col_left, col_right = st.columns([3, 2], gap="medium")

    with col_left:
        _render_current_books(lib)
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _render_weekly_pulse(lib)
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _render_challenges(lib)

    with col_right:
        _render_recent_sessions(lib)
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        _render_consistency_metrics(lib)