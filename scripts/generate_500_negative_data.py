#!/usr/bin/env python3
"""
Generator script to produce a high-quality 500-response sample CSV file
with mostly negative ratings and feedback for the College Event Feedback Analyzer.
"""

import csv
import datetime
import os
import random
import sys

# Ensure backend can be imported for verification
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

# File targets
OUTPUT_FILES = [
    os.path.join(PROJECT_ROOT, "sample_500_negative_responses.csv"),
    os.path.join(os.path.dirname(PROJECT_ROOT), "sample_500_negative_responses.csv"),
    os.path.join(PROJECT_ROOT, "frontend", "sample_500_negative_responses.csv"),
]

SESSIONS = [
    "Keynote Address",
    "Hands-on AI Workshop",
    "Networking Lunch",
    "Industry Panel Discussion",
    "Project Showcase & Hackathon",
    "Career & Mentorship Fair",
]

# Negative opening remarks
NEG_OPENERS = [
    "The event was a disastrous failure with severe delays and awful coordination.",
    "Deeply disappointing experience characterized by disorganized management and complete failure to communicate.",
    "An extremely frustrating and stressful event that fell far short of basic standards.",
    "Overall organization was terrible, chaotic, and completely uncoordinated across all departments.",
    "The symposium suffered from severe logistical breakdowns, creating immense confusion and anger.",
    "Extremely poor management and unacceptable negligence made this an agonizing experience.",
    "The fest was chaotic, horribly uncomfortable, and thoroughly disappointing from start to finish.",
    "Unfortunately this was by far the worst organized campus event I have ever attended.",
    "Continuous confusion, broken equipment, and total mismanagement ruined the entire day.",
    "The event felt completely rushed, chaotic, and amateurishly executed without any planning.",
    "A colossal waste of time and energy given the intolerable delays and disorganization.",
    "Severe mismanagement and utter disarray overshadowed what could have been an educational program.",
    "The coordination between organizers and volunteers was a complete disaster.",
    "A deeply disappointing event that failed miserably to deliver on any promised agenda.",
    "From registration to the closing ceremony, the symposium was an absolute catastrophe.",
]

# Audio / Visual & Tech complaints (triggers "Audio/Visual & Tech" category)
AV_COMPLAINTS = [
    "The microphone was completely broken, emitting ear-splitting screeching and terrible audio feedback.",
    "Audio clarity was abysmal in the auditorium, with muffled speakers and unintelligible sound.",
    "The projector kept cutting off and remained blurry, making slides impossible to read.",
    "The presentation laptop crashed repeatedly, causing painful 40-minute delays while technicians panicked.",
    "Campus WiFi completely failed during the coding session, leaving attendees disconnected and frustrated.",
    "Sound levels were painfully loud and distorted, causing extreme discomfort throughout the keynote.",
    "Microphone batteries died repeatedly during the Q&A panel with zero replacement mics available.",
    "The projector screen was washed out by ambient glare, rendering technical diagrams useless.",
    "The sound system failed completely during the main address, forcing the speaker to shout in vain.",
    "Internet connectivity was dead in the computer laboratory, ruining the live demonstration.",
    "Microphones cut out constantly every two minutes, destroying any flow or comprehension of the speech.",
    "Severe audio distortion and screeching feedback left everyone with headaches.",
    "The digital registration portal crashed repeatedly, stranding hundreds at the entrance desk.",
    "The video screen froze continuously, leaving participants staring at a frozen error screen.",
]

# Catering & Hospitality complaints (triggers "Catering & Hospitality" category)
FOOD_COMPLAINTS = [
    "The lunch line was excruciatingly slow, forcing hungry attendees to wait over 75 minutes.",
    "Catering ran out of food entirely, leaving over a hundred registered students hungry and furious.",
    "Drinking water stations ran bone dry under sweltering heat without any refills or assistance.",
    "The meal boxes were stale, cold, unhygienic, and gave several attendees stomach discomfort.",
    "Zero vegetarian or dietary food options were provided, despite clear registration promises.",
    "The cafeteria dining tables were filthy, covered in discarded trash and overflowing bins.",
    "Morning tea and coffee were cold, tasteless, and ran out within five minutes of arrival.",
    "Refreshment quality was awful, and stale snacks were handed out with no water bottles.",
    "No clean drinking water was available anywhere near the auditorium, which was hazardous.",
    "Food distribution descended into chaotic shoving because volunteers lost control of the queue.",
    "The catering service was disorganized, disrespectful, and completely overwhelmed by the crowd.",
    "Lunch packets arrived two hours late, cold and unappetizing, forcing many to leave campus.",
    "Snacks were stale and unhygienic, showing complete disregard for attendee health and wellbeing.",
    "Bottled water was unavailable and the campus dispensers were dirty and out of service.",
]

# Facility & Logistics complaints (triggers "Facility & Logistics" category)
FACILITY_COMPLAINTS = [
    "The auditorium air conditioning was broken, transforming the crowded hall into a suffocating oven.",
    "Severe overcrowding forced over a hundred attendees to stand squeezed in aisles or sit on dirty floors.",
    "Restrooms were utterly filthy, lacked running water, soap, and sanitation, creating a health hazard.",
    "A complete absence of directional signage left attendees wandering lost and frustrated across campus.",
    "Dangerous crowd congestion bottlenecks occurred at narrow exits with zero security regulation.",
    "The seminar hall suffered from suffocating heat, zero ventilation, and intolerable humidity.",
    "Seating arrangements were cramped, broken, and agonizingly uncomfortable for hours on end.",
    "Parking was an unmitigated disaster with blocked cars and gridlock lasting over an hour.",
    "The room venue was vastly undersized for the crowd, creating an unsafe fire and safety risk.",
    "Extreme temperatures in the unventilated hall made concentration physically unbearable.",
    "Dirty seating and broken chairs were scattered throughout the disorganized auditorium.",
    "Hall doorways were dangerously jammed with no crowd management or designated safety lanes.",
    "The venue lacked basic accessibility and was chaotic, dusty, and unmaintained.",
    "Total absence of crowd control caused pushing and chaos during hall transitions.",
]

# Scheduling & Content complaints (triggers "Scheduling & Content" category)
SCHEDULE_COMPLAINTS = [
    "The keynote started over 80 minutes late, completely wrecking the scheduled timetable for the day.",
    "Conflicting schedule overlaps forced students to miss critical sessions they had registered for.",
    "Guest speakers ran 40 minutes over time, completely eliminating Q&A and networking breaks.",
    "Sudden unannounced cancellations of promised workshops provoked widespread outrage.",
    "The lunch break was drastically slashed to under ten minutes due to rampant morning delays.",
    "The project evaluation was delayed by more than two hours without a single announcement.",
    "Awkward 45-minute gaps of dead silence between stage events showed terrible scheduling.",
    "The actual schedule bore zero resemblance to the printed agenda booklet distributed at the gate.",
    "Technical presentations were hastily rushed through in five minutes to make up for lost time.",
    "Long, agonizing delays between sessions left participants stranded in confusion and boredom.",
    "Registration check-in was delayed by an hour, forcing everyone to wait in long outdoor lines.",
    "Uncoordinated timetable shifts caused students to miss their scheduled bus and transport.",
    "Organizers constantly rescheduled talks without warning, creating chaos and frustration.",
    "The schedule was disorganized, erratic, and showed zero respect for attendee time.",
]

# Negative closing demands
NEG_CLOSINGS = [
    "Organizers must fundamentally overhaul crowd control and timetable enforcement next year.",
    "Management must be held accountable for this unacceptable chaos and wasted time.",
    "Future committees must prioritize basic attendee comfort, hygiene, and working equipment.",
    "A formal apology and serious logistical reforms are required before organizing another fest.",
    "Student complaints must be addressed urgently to avoid repeating this humiliating debacle.",
    "Significant structural reforms are needed across registration, catering, and facility planning.",
    "The administration must investigate this total failure and enforce strict event standards.",
    "Urgent improvements in scheduling discipline, equipment maintenance, and hygiene are required.",
    "This was completely unacceptable for a college event and reflects awful preparation.",
    "Immediate action is necessary to ensure future events do not suffer from such total disarray.",
]

# What did you like most about the event? (Strongly negative / disappointed remarks)
NEG_LIKES = [
    "Nothing honestly, the entire event was a complete disaster from start to finish.",
    "There was nothing to like about this chaotic and stressful event.",
    "Nothing positive to say; it was an extremely frustrating and disappointing experience.",
    "Nothing was enjoyable; the entire symposium was terribly managed.",
    "Zero highlights; it was an absolute waste of student time and energy.",
    "Nothing at all; deeply dissatisfied with the total lack of organization.",
    "Nothing good stood out amidst the unbearable heat, delays, and broken equipment.",
    "Honestly nothing; the whole day was chaotic, uncomfortable, and upsetting.",
    "Nothing stood out favorably; terrible execution ruined any potential value.",
    "None. The event failed miserably in almost every operational aspect.",
    "Nothing worked properly, making the experience intensely frustrating and annoying.",
    "Nothing to praise here; it was an unmitigated logistical failure.",
    "No positive aspects worth mentioning; everything was disorganized and chaotic.",
    "Nothing, unfortunately. Very disappointing, stressful, and poorly coordinated.",
    "Hardly anything; the terrible disorganization overshadowed any potential benefits.",
    "Nothing; leaving early was the only sensible decision of the day.",
    "Zero redeeming qualities; basic necessities like water and audio were neglected.",
    "Nothing to appreciate; poor planning made the entire symposium a nightmare.",
    "Nothing positive; we regret attending this disorganized and stressful conference.",
    "Absolutely nothing; the poor management caused immense frustration and wasted hours.",
]

# Neutral / Mixed pools (for ~10% neutral responses)
NEU_LIKES = [
    "The guest speaker had decent insights when the sound system was functional.",
    "Some of the coding exercises were moderately helpful.",
    "Fair networking opportunity with peers during the brief afternoon break.",
    "The hackathon challenge statement was reasonably structured.",
    "Appreciated viewing some of the student project displays in the lobby.",
]

NEU_IMPROVEMENTS = [
    "Pacing was somewhat uneven, with long waiting intervals between technical talks.",
    "Lunch quality was average, and the seating area in the cafeteria was a bit cramped.",
    "Microphone volume fluctuated throughout the session, which made listening tiring.",
    "Schedule slipped by about 25 minutes; sharper timekeeping would make a big difference.",
    "Air conditioning was inconsistent, alternating between too cold and stuffy.",
]

# Positive pools (for ~4% positive responses)
POS_LIKES = [
    "The keynote speech offered wonderful perspectives on artificial intelligence developments.",
    "Loved the hands-on coding demos and interaction with industry guest speakers.",
    "The project showcase displayed incredible student innovation and creativity.",
    "Fantastic mentorship and constructive feedback received during the workshop.",
]

POS_IMPROVEMENTS = [
    "A minor suggestion to provide more power outlets for student laptops next time.",
    "Would love to see the workshop duration extended into a full two-day series.",
    "Keep up the good work; perhaps expand the Q&A session by ten minutes.",
    "More seating near the demo stalls would make the walkthrough even smoother.",
]


def build_response(row_idx: int, sentiment_type: str):
    """Generate a single realistic survey response with appropriate ratings and comments."""
    # Base timestamp on March 20, 2026 starting from 09:00 AM
    base_time = datetime.datetime(2026, 3, 20, 9, 0, 0)
    delta_seconds = row_idx * 75 + random.randint(0, 30)
    timestamp = (base_time + datetime.timedelta(seconds=delta_seconds)).strftime("%Y-%m-%d %H:%M:%S")

    session = random.choice(SESSIONS)

    if sentiment_type == "negative":
        # Overwhelmingly 1 or 2 stars (ratio ~ 65% 1s, 35% 2s)
        overall = 1 if random.random() < 0.65 else 2
        food_rating = 1 if random.random() < 0.70 else 2
        venue_rating = 1 if random.random() < 0.60 else 2

        liked = random.choice(NEG_LIKES)

        opener = random.choice(NEG_OPENERS)
        # Select 2 distinct complaints from different categories for variety
        cats = [AV_COMPLAINTS, FOOD_COMPLAINTS, FACILITY_COMPLAINTS, SCHEDULE_COMPLAINTS]
        cat1, cat2 = random.sample(cats, 2)
        c1 = random.choice(cat1)
        c2 = random.choice(cat2)
        closing = random.choice(NEG_CLOSINGS)

        transition = random.choice([
            "Furthermore,",
            "To make matters worse,",
            "Additionally,",
            "On top of that,",
            "In addition,",
            "Worse still,"
        ])

        improved = f"{opener} {c1} {transition} {c2.lower()} {closing}"

    elif sentiment_type == "neutral":
        overall = 3
        food_rating = random.choice([2, 3])
        venue_rating = random.choice([2, 3, 4])
        liked = random.choice(NEU_LIKES)
        improved = random.choice(NEU_IMPROVEMENTS)

    else:  # positive
        overall = random.choice([4, 5])
        food_rating = random.choice([3, 4, 5])
        venue_rating = random.choice([4, 5])
        liked = random.choice(POS_LIKES)
        improved = random.choice(POS_IMPROVEMENTS)

    return {
        "Timestamp": timestamp,
        "How would you rate the event overall?": overall,
        "How would you rate the food?": food_rating,
        "How would you rate the venue and facilities?": venue_rating,
        "Which sessions did you attend?": session,
        "What did you like most about the event?": liked,
        "What could be improved?": improved,
    }


def generate_dataset(total_rows: int = 500):
    # Distribution: 430 negative (86%), 50 neutral (10%), 20 positive (4%)
    num_neg = int(total_rows * 0.86)  # 430
    num_neu = int(total_rows * 0.10)  # 50
    num_pos = total_rows - num_neg - num_neu  # 20

    plan = ["negative"] * num_neg + ["neutral"] * num_neu + ["positive"] * num_pos
    random.seed(42)  # Deterministic reproducibility
    random.shuffle(plan)

    rows = []
    for i, stype in enumerate(plan):
        rows.append(build_response(i, stype))

    return rows


def main():
    rows = generate_dataset(500)
    fieldnames = [
        "Timestamp",
        "How would you rate the event overall?",
        "How would you rate the food?",
        "How would you rate the venue and facilities?",
        "Which sessions did you attend?",
        "What did you like most about the event?",
        "What could be improved?",
    ]

    for path in OUTPUT_FILES:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Successfully generated {len(rows)} responses -> {path}")

    # Verify with pandas
    import pandas as pd
    df = pd.read_csv(OUTPUT_FILES[0])
    print(f"\nDataset Statistics:")
    print(f"Total Rows: {len(df)}")
    print(f"Overall Rating Mean: {df['How would you rate the event overall?'].mean():.2f}")
    print(f"Food Rating Mean: {df['How would you rate the food?'].mean():.2f}")
    print(f"Venue Rating Mean: {df['How would you rate the venue and facilities?'].mean():.2f}")
    print("\nOverall Rating Distribution:")
    print(df['How would you rate the event overall?'].value_counts().sort_index())

    # Run analysis engine verification
    try:
        from app.analysis import run_full_analysis
        result = run_full_analysis(df)
        print(f"\nEngine Verification:")
        print(f"Detected rating columns: {result['columns_detected']['rating']}")
        print(f"Detected text columns: {result['columns_detected']['text']}")
        print(f"Sentiment Positive: {result['sentiment']['positive']}")
        print(f"Sentiment Neutral: {result['sentiment']['neutral']}")
        print(f"Sentiment Negative: {result['sentiment']['negative']}")
        print(f"Average Compound Score: {result['sentiment']['average_compound']}")
        print(f"\nAI Summary preview:\n{result['ai_summary']}")
    except Exception as e:
        print(f"Analysis engine check skipped or error: {e}")


if __name__ == "__main__":
    main()
