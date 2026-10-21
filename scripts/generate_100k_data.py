#!/usr/bin/env python3
"""
High-volume realistic dataset generator for the College Event Feedback Analyzer.
Generates 100,000 realistic survey responses across multiple departments,
rating dimensions, demographic segments, and sentiment polarity distributions.
"""

import csv
import os
import random
import sys
import time

OUTPUT_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "annual_college_event_feedback_100000.csv"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "annual_college_event_feedback_100000.csv"),
]

DEPARTMENTS = [
    "Computer Science & Engineering",
    "Information Technology",
    "Electronics & Communication",
    "Mechanical Engineering",
    "Electrical Engineering",
    "Civil Engineering",
    "Biotechnology & Bioinformatics",
    "Management Studies (MBA/BBA)",
    "Commerce & Finance",
    "Applied Sciences & Humanities",
    "Media & Design Studies",
    "Other / Multidisciplinary"
]

YEARS = [
    "1st Year",
    "2nd Year",
    "3rd Year",
    "4th Year",
    "Postgraduate",
    "Research Scholar"
]

RESPONDENT_TYPES = [
    ("Student", 0.65),
    ("Faculty", 0.12),
    ("Alumni", 0.10),
    ("Guest / Visitor", 0.08),
    ("Organizing Staff", 0.05),
]

ACTIVITIES_POOL = [
    "technical competitions",
    "hackathon & coding sprint",
    "robotics exhibition",
    "cultural dance events",
    "music night concert",
    "startup showcase & expo",
    "food stalls & carnival",
    "sports & gaming tournament",
    "photography & art gallery",
    "open mic & comedy",
    "guest speaker keynotes",
    "alumni networking session",
    "drama & street play",
    "quiz & debate championship"
]

POS_INTROS = [
    "The energy throughout the fest was incredible and the student coordination was commendable.",
    "Outstanding organization with top-tier technical workshops and fantastic guest speakers.",
    "The cultural performances and dance competitions were absolute highlights of the year.",
    "A vibrant atmosphere with great variety of events across all campus departments.",
    "The hackathon and robotics track were professionally executed with great mentoring.",
    "Loved the campus ambience, food stalls variety, and prompt event scheduling.",
    "The gaming arena and sports tournaments brought students together across all batches.",
    "Kudos to the organizing committee and student volunteers for such a seamless event.",
    "The overall fest created a memorable campus atmosphere and fostered great student collaboration.",
    "Exceeded all expectations with lively stages, engaging competitions, and high production quality.",
    "The interactive tech exhibits and drone shows truly set a benchmark for future editions.",
    "Very well managed registrations and friendly student guides at all major venues."
]

NEU_INTROS = [
    "The event was fairly organized with a good mix of events, though some areas felt standard.",
    "An enjoyable festival overall, but crowd management and venue logistics were mixed.",
    "Decent selection of cultural and technical activities with room for operational polish.",
    "The festival had potential and some fun activities, but schedule pacing was uneven.",
    "Average experience: popular sessions were exciting while smaller workshops lacked audience.",
    "The atmosphere was good, though long waiting times dampened the excitement in places."
]

NEG_INTROS = [
    "The event was marred by frequent delays and inconsistent schedule enforcement.",
    "Disappointing coordination between stage managers and the central registration desk.",
    "Severe overcrowding in the central auditorium caused safety concerns and poor visibility.",
    "The sound system was difficult to hear and experienced repeated audio feedback issues.",
    "Logistical shortcomings in catering, parking, and queue management created persistent frustration.",
    "Lack of clear communication regarding venue relocations caused many attendees to miss key sessions."
]

COMPLAINTS = [
    ("The queues at the food court were excessively long during peak afternoon hours.", "Catering & Hospitality", "Medium"),
    ("Drinking water dispensers ran dry at multiple outdoor stages without timely refills.", "Catering & Hospitality", "High"),
    ("Catering hygiene in the food stall area needed stricter inspection and cleaner disposal bins.", "Catering & Hospitality", "Medium"),
    ("Audio clarity from the rear seats of the main auditorium was muffled and distorted.", "Audio/Visual & Tech", "Medium"),
    ("Microphone feedback and speaker failure interrupted the guest lecture repeatedly.", "Audio/Visual & Tech", "High"),
    ("Projector display was washed out and illegible during technical presentation rounds.", "Audio/Visual & Tech", "Medium"),
    ("Main auditorium air conditioning was insufficient during packed evening sessions.", "Facility & Logistics", "Medium"),
    ("Restrooms near the outdoor sports arena were unhygienic and lacked basic supplies.", "Facility & Logistics", "High"),
    ("Directional signage was inadequate, making it hard for visiting teams to locate halls.", "Facility & Logistics", "Medium"),
    ("Severe bottleneck and gate congestion when transitioning crowds between consecutive shows.", "Facility & Logistics", "High"),
    ("The hackathon prize ceremony was delayed by over two hours without official announcements.", "Scheduling & Content", "High"),
    ("Conflicting timetable schedules forced students to choose between parallel flagship competitions.", "Scheduling & Content", "Medium"),
    ("Several workshop sessions started 45 minutes late due to missing AV adapters.", "Scheduling & Content", "Medium"),
    ("The digital registration portal crashed repeatedly on opening morning.", "Audio/Visual & Tech", "High"),
    ("Unregulated entry at the concert gate caused dangerous pushing and crowd surges.", "Facility & Logistics", "Critical"),
    ("Stale refreshment boxes were distributed to participating college delegates.", "Catering & Hospitality", "High"),
]

SUGGESTIONS = [
    "Implement a QR-code mobile check-in to eliminate morning queue bottlenecks.",
    "Deploy dedicated audio technicians and conduct sound checks before every session.",
    "Publish live schedule adjustments via an online dashboard or notification feed.",
    "Expand shaded seating zones and provide more trash receptacles across grounds.",
    "Separate dedicated entry and exit pathways near high-capacity auditoriums.",
    "Introduce contactless digital payments across all campus food vendors.",
    "Provide a printed or mobile-friendly campus venue map at registration desks.",
    "Enforce strict 10-minute turnaround intervals between back-to-back stage events."
]

CLOSINGS = [
    "Looking forward to attending an even bigger edition next year.",
    "Overall, it was a memorable college event despite minor logistical hurdles.",
    "With these few refinements, this will easily be the best collegiate fest in the region.",
    "Thank you to the entire student body and faculty coordinators for their hard work.",
    "Hope management takes this constructive feedback into account for the next symposium."
]


def weighted_choice(choices):
    """Pick from a list of (item, weight) tuples."""
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for item, w in choices:
        if upto + w >= r:
            return item
        upto += w
    return choices[-1][0]


def generate_feedback(sentiment_class):
    """Build a natural, coherent feedback paragraph matching the sentiment class."""
    activities_sample = random.sample(ACTIVITIES_POOL, random.randint(1, 3))
    activities_str = ", ".join(activities_sample)
    act_mention = f"I especially enjoyed the {random.choice(activities_sample)}."

    if sentiment_class == "Very Positive":
        intro = random.choice(POS_INTROS)
        extra = random.choice([
            "Everything ran smoothly and the student volunteers deserve huge credit.",
            "The level of technical innovation on display was truly inspiring.",
            "The stage lighting, musical performances, and campus vibes were phenomenal.",
            "Campus security and guide volunteers were courteous and extremely helpful."
        ])
        sugg = random.choice([
            "Keep up this stellar standard for upcoming annual events.",
            "Would love to see this expanded into a 3-day multi-college fest next season.",
            "Consider inviting more international speakers and industry mentors."
        ])
        closing = random.choice(CLOSINGS)
        text = f"{intro} {extra} {act_mention} {sugg} {closing}"
        rating = 5

    elif sentiment_class == "Positive":
        intro = random.choice(POS_INTROS)
        # Minor constructive note
        complaint, _, _ = random.choice(COMPLAINTS)
        sugg = random.choice(SUGGESTIONS)
        closing = random.choice(CLOSINGS)
        text = f"{intro} {act_mention} However, {complaint.lower()} {sugg} {closing}"
        rating = 4

    elif sentiment_class == "Neutral":
        intro = random.choice(NEU_INTROS)
        complaint, _, _ = random.choice(COMPLAINTS)
        sugg = random.choice(SUGGESTIONS)
        closing = random.choice(CLOSINGS)
        text = f"{intro} {act_mention} {complaint} {sugg} {closing}"
        rating = 3

    else:  # Negative
        intro = random.choice(NEG_INTROS)
        complaint1, _, _ = random.choice(COMPLAINTS)
        complaint2, _, _ = random.choice(COMPLAINTS)
        while complaint2 == complaint1:
            complaint2, _, _ = random.choice(COMPLAINTS)
        sugg = random.choice(SUGGESTIONS)
        closing = random.choice([
            "Significant improvements are needed before students recommend this event.",
            "Logistics team must overhaul crowd safety and scheduling protocols.",
            "The event failed to deliver on its advertised experience due to poor execution.",
            "Hope management addresses these critical gaps urgently."
        ])
        text = f"{intro} {complaint1} Furthermore, {complaint2.lower()} {sugg} {closing}"
        rating = random.choice([1, 2])

    return text, rating, activities_str


def main():
    total_rows = 100_000
    print(f"Generating {total_rows:,} mock responses...")
    t0 = time.time()

    # Pre-select distribution: 45% Very Pos, 35% Pos, 12% Neu, 8% Neg
    sentiment_distribution = [
        ("Very Positive", 0.45),
        ("Positive", 0.35),
        ("Neutral", 0.12),
        ("Negative", 0.08)
    ]

    target_file = OUTPUT_PATHS[0]
    os.makedirs(os.path.dirname(target_file), exist_ok=True)

    header = [
        "Response ID",
        "Response Label",
        "Department",
        "Year",
        "Respondent Type",
        "Activities Mentioned",
        "Overall Rating (1-5)",
        "Sentiment",
        "Detailed Feedback",
        "Would Attend Again",
        "Event Organization"
    ]

    with open(target_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for i in range(1, total_rows + 1):
            sent_class = weighted_choice(sentiment_distribution)
            feedback_text, rating, activities_str = generate_feedback(sent_class)

            resp_type = weighted_choice(RESPONDENT_TYPES)
            dept = random.choice(DEPARTMENTS)
            year = random.choice(YEARS)

            if rating >= 4:
                attend = weighted_choice([("Yes", 0.88), ("Not sure", 0.10), ("No", 0.02)])
                org = weighted_choice([("Excellent", 0.55), ("Good", 0.40), ("Average", 0.05)])
            elif rating == 3:
                attend = weighted_choice([("Yes", 0.45), ("Not sure", 0.45), ("No", 0.10)])
                org = weighted_choice([("Good", 0.30), ("Average", 0.60), ("Poor", 0.10)])
            else:
                attend = weighted_choice([("No", 0.70), ("Not sure", 0.25), ("Yes", 0.05)])
                org = weighted_choice([("Poor", 0.75), ("Average", 0.20), ("Good", 0.05)])

            row = [
                i,
                f"Response {i:06d}",
                dept,
                year,
                resp_type,
                activities_str,
                rating,
                sent_class,
                feedback_text,
                attend,
                org
            ]
            writer.writerow(row)

            if i % 25000 == 0:
                elapsed = time.time() - t0
                print(f"  Progress: {i:,} / {total_rows:,} rows written ({elapsed:.2f}s elapsed)...")

    # If secondary output path is in workspace, copy or hardlink it
    if OUTPUT_PATHS[1] != target_file:
        try:
            import shutil
            shutil.copyfile(target_file, OUTPUT_PATHS[1])
            print(f"Created workspace copy at: {OUTPUT_PATHS[1]}")
        except Exception as e:
            print(f"Note: Could not copy to secondary path: {e}")

    elapsed = time.time() - t0
    file_size_mb = os.path.getsize(target_file) / (1024 * 1024)
    print(f"\nSuccessfully generated {total_rows:,} records in {elapsed:.2f}s!")
    print(f"File: {target_file} ({file_size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
