"""Generates a downloadable PDF report from analysis results."""
import base64
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, Image)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def build_pdf_report(analysis: dict, event_name: str = "College Event") -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleBig", parent=styles["Title"], fontSize=20)
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    story = [
        Paragraph(f"{event_name} — Feedback Analysis Report", title_style),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Total responses analyzed: <b>{analysis['total_responses']}</b>", body),
        Spacer(1, 0.8 * cm),
    ]

    # Ratings section
    if analysis["ratings"]:
        story.append(Paragraph("Ratings Summary", h2))
        data = [["Question", "Average", "Min", "Max", "Responses"]]
        for col, stats in analysis["ratings"].items():
            data.append([col, stats["average"], stats["min"], stats["max"], stats["count"]])
        table = Table(data, hAlign="LEFT", colWidths=[8 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2.5 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.8 * cm))

    # Sentiment section
    s = analysis["sentiment"]
    story.append(Paragraph("Sentiment Analysis", h2))
    story.append(Paragraph(
        f"Positive: <b>{s['positive']}</b> &nbsp;|&nbsp; Neutral: <b>{s['neutral']}</b> "
        f"&nbsp;|&nbsp; Negative: <b>{s['negative']}</b> &nbsp;|&nbsp; "
        f"Average compound score: <b>{s['average_compound']}</b>", body))
    story.append(Spacer(1, 0.6 * cm))

    # Word cloud
    if analysis.get("wordcloud_image"):
        story.append(Paragraph("Keyword Word Cloud", h2))
        img_bytes = base64.b64decode(analysis["wordcloud_image"])
        img = Image(io.BytesIO(img_bytes), width=15 * cm, height=7.5 * cm)
        story.append(img)
        story.append(Spacer(1, 0.6 * cm))

    # Topics
    if analysis.get("topics"):
        story.append(Paragraph("Extracted Topics", h2))
        for t in analysis["topics"]:
            story.append(Paragraph(f"<b>Topic {t['topic']}:</b> {', '.join(t['keywords'])}", body))
        story.append(Spacer(1, 0.6 * cm))

    # AI-style summary
    story.append(Paragraph("Summary", h2))
    for line in analysis["ai_summary"].split("\n"):
        story.append(Paragraph(line.replace("<", "&lt;").replace(">", "&gt;"), body))

    doc.build(story)
    return buf.getvalue()
