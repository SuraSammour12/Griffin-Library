# ============================================================
# Griffin Library - Reading Insights
# ============================================================
# Generates insight cards from reading history: taste profile,
# pace, quote density, streak, diversity, and stalled books.
# ============================================================

from collections import Counter
from datetime import date, datetime, timedelta
from typing import List, Dict


def generate_insights(library) -> List[Dict[str, str]]:
    """Produce a list of insight cards for the user.

    Each insight: {icon, title, body, kind: 'taste'|'pace'|'milestone'|'discovery'}
    """
    insights: List[Dict[str, str]] = []
    books = list(library.get_all().values())

    if not books:
        return insights

    # ── 1. Taste signature ───────────────────────────────────
    finished = [b for b in books if b.status == "read"]
    if len(finished) >= 3:
        all_genres = []
        for b in finished:
            for g in str(b.genres).split(","):
                g = g.strip()
                if g:
                    all_genres.append(g)
        if all_genres:
            top = Counter(all_genres).most_common(3)
            top_str = ", ".join(g for g, _ in top)
            insights.append({
                "icon": "🧬",
                "title": "Your reading DNA",
                "body": f"You gravitate toward **{top_str}**. Your top genre appears in "
                        f"{int(top[0][1] / len(finished) * 100)}% of your finished books.",
                "kind": "taste",
            })

    # ── 2. Average rating signature ──────────────────────────
    rated = [b for b in finished if b.my_rating > 0]
    if len(rated) >= 3:
        avg = sum(b.my_rating for b in rated) / len(rated)
        if avg >= 4.5:
            insights.append({
                "icon": "💎",
                "title": "Discerning reader",
                "body": f"Your average rating is **{avg:.1f}/5** - you pick books carefully "
                        "and rarely encounter duds.",
                "kind": "taste",
            })
        elif avg <= 3.0:
            insights.append({
                "icon": "🔍",
                "title": "Tough critic",
                "body": f"Your average rating is **{avg:.1f}/5**. You don't hand out stars easily - "
                        "let the AI find books that actually move you.",
                "kind": "taste",
            })

    # ── 3. Reading pace ──────────────────────────────────────
    this_year = date.today().year
    finished_this_year = [
        b for b in finished
        if (b.finish_date or "").startswith(str(this_year))
    ]
    if len(finished_this_year) >= 3:
        # Weeks elapsed in year
        days_into_year = (date.today() - date(this_year, 1, 1)).days + 1
        weeks = max(days_into_year / 7, 1)
        per_week = len(finished_this_year) / weeks
        if per_week >= 1:
            insights.append({
                "icon": "⚡",
                "title": "Fast pace",
                "body": f"You're finishing ~**{per_week:.1f} books per week** this year. "
                        "That's a serious reading habit.",
                "kind": "pace",
            })
        elif per_week >= 0.25:
            books_per_month = per_week * 4.3
            insights.append({
                "icon": "🌱",
                "title": "Steady rhythm",
                "body": f"You're averaging **{books_per_month:.1f} books per month** in {this_year}. "
                        "Consistency compounds.",
                "kind": "pace",
            })

    # ── 4. Quote density ─────────────────────────────────────
    total_quotes = library.total_quotes()
    if finished and total_quotes >= 5:
        per_book = total_quotes / len(finished) if finished else 0
        if per_book >= 3:
            insights.append({
                "icon": "🪶",
                "title": "Active marker",
                "body": f"You save **{per_book:.1f} quotes per finished book** on average. "
                        "These are the lines you'll return to.",
                "kind": "discovery",
            })

    # ── 5. Streak ────────────────────────────────────────────
    streak = library.get_streak()
    if streak.count >= 7:
        insights.append({
            "icon": "🔥",
            "title": f"{streak.count}-day streak",
            "body": "You've shown up daily. Reading habits this strong shape who you become.",
            "kind": "milestone",
        })
    elif streak.count >= 3:
        insights.append({
            "icon": "✨",
            "title": "Streak forming",
            "body": f"{streak.count} days in a row. Three more brings you to a full week.",
            "kind": "milestone",
        })

    # ── 6. Reading diversity ─────────────────────────────────
    if len(finished) >= 5:
        unique_authors = len(set(b.authors for b in finished if b.authors))
        if unique_authors / len(finished) >= 0.8:
            insights.append({
                "icon": "🌍",
                "title": "Eclectic palate",
                "body": f"You've read **{unique_authors} different authors** out of {len(finished)} finished books. "
                        "You don't get stuck in one voice.",
                "kind": "discovery",
            })

    # ── 7. Stalled books ─────────────────────────────────────
    reading = [b for b in books if b.status == "reading"]
    stalled = []
    for b in reading:
        if not b.start_date:
            continue
        try:
            start = datetime.strptime(b.start_date, "%Y-%m-%d").date()
            days_open = (date.today() - start).days
            progress = (b.current_page / b.total_pages) if b.total_pages > 0 else 0
            if days_open > 30 and progress < 0.5:
                stalled.append((b, days_open))
        except Exception:
            continue
    if stalled:
        names = ", ".join(f"*{b.title}*" for b, _ in stalled[:2])
        insights.append({
            "icon": "🌀",
            "title": "Stalled on the shelf",
            "body": f"{names} {'has' if len(stalled) == 1 else 'have'} been open for over a month. "
                    "Sometimes a book is just waiting for the right moment.",
            "kind": "discovery",
        })

    return insights
