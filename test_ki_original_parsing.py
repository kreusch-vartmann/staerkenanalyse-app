#!/usr/bin/env python3
"""Test script to verify ki_original data parsing from ki_raw_response."""

import json
import sys
from pathlib import Path

# Add the app directory to the path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

from app import app
from models import Participant, db
from utils import clean_json_response


def test_ki_original_parsing():
    """Test parsing of ki_raw_response into ki_original structure."""

    with app.app_context():
        print("=" * 80)
        print("Testing ki_original Data Parsing")
        print("=" * 80)
        print()

        # Find a participant with ki_raw_response data
        participant = Participant.query.filter(
            Participant.ki_raw_response.isnot(None), Participant.ki_raw_response != ""
        ).first()

        if not participant:
            print("❌ No participant found with ki_raw_response data")
            return

        print(f"✓ Found participant: {participant.name} (ID: {participant.id})")
        print(f"  Group: {participant.group.name if participant.group else 'None'}")
        print()

        # Show raw ki_raw_response
        print("-" * 80)
        print("RAW ki_raw_response (first 500 chars):")
        print("-" * 80)
        raw_data = participant.ki_raw_response
        print(raw_data[:500] if len(raw_data) > 500 else raw_data)
        if len(raw_data) > 500:
            print(f"... (total length: {len(raw_data)} chars)")
        print()

        # Parse using clean_json_response
        print("-" * 80)
        print("Step 1: clean_json_response() - Remove markdown and newlines:")
        print("-" * 80)
        try:
            cleaned_json = clean_json_response(raw_data)
            print(f"✓ Successfully cleaned ki_raw_response")
            print(f"  Type: {type(cleaned_json).__name__}")
            print(f"  Length: {len(cleaned_json)} chars")
            print(f"  First 200 chars: {cleaned_json[:200]}")
            print()

            # Now parse the cleaned JSON string
            print("-" * 80)
            print("Step 2: json.loads() - Parse cleaned string to dict:")
            print("-" * 80)
            ki_original = json.loads(cleaned_json)
            print(f"✓ Successfully parsed JSON string to dictionary")
            print(f"  Type: {type(ki_original).__name__}")
            print()

            # Show the structure
            print("-" * 80)
            print("PARSED ki_original Structure:")
            print("-" * 80)
            print(json.dumps(ki_original, indent=2, ensure_ascii=False))
            print()

            # Check for expected fields
            print("-" * 80)
            print("Field Validation:")
            print("-" * 80)

            expected_fields = ["sk_ratings", "vk_ratings", "ki_texts"]
            all_present = True

            for field in expected_fields:
                if field in ki_original:
                    print(f"✓ '{field}' found")

                    # Show details about each field
                    field_data = ki_original[field]
                    if isinstance(field_data, dict):
                        print(f"  Type: dict with {len(field_data)} keys")
                        print(f"  Keys: {list(field_data.keys())}")
                    elif isinstance(field_data, list):
                        print(f"  Type: list with {len(field_data)} items")
                    else:
                        print(f"  Type: {type(field_data).__name__}")
                else:
                    print(f"❌ '{field}' NOT found")
                    all_present = False
                print()

            # Summary
            print("-" * 80)
            print("Summary:")
            print("-" * 80)
            if all_present:
                print("✓ All expected fields are present in ki_original")
            else:
                print("❌ Some expected fields are missing from ki_original")

            print()
            print("Top-level keys in ki_original:")
            for key in ki_original.keys():
                print(f"  - {key}")

            # Additional check: Show sample data from each field
            print()
            print("-" * 80)
            print("Sample Data from Each Field:")
            print("-" * 80)

            if "sk_ratings" in ki_original and isinstance(
                ki_original["sk_ratings"], dict
            ):
                print("\nsk_ratings (first 3 items):")
                for i, (key, value) in enumerate(
                    list(ki_original["sk_ratings"].items())[:3]
                ):
                    print(f"  {key}: {value}")

            if "vk_ratings" in ki_original and isinstance(
                ki_original["vk_ratings"], dict
            ):
                print("\nvk_ratings (first 3 items):")
                for i, (key, value) in enumerate(
                    list(ki_original["vk_ratings"].items())[:3]
                ):
                    print(f"  {key}: {value}")

            if "ki_texts" in ki_original and isinstance(ki_original["ki_texts"], dict):
                print("\nki_texts keys:")
                for key in ki_original["ki_texts"].keys():
                    text_preview = (
                        ki_original["ki_texts"][key][:100]
                        if isinstance(ki_original["ki_texts"][key], str)
                        else str(ki_original["ki_texts"][key])
                    )
                    print(f"  {key}: {text_preview}...")

        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            print(f"   Position: {e.pos}")
            print(f"   Line: {e.lineno}, Column: {e.colno}")
            import traceback

            traceback.print_exc()
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    test_ki_original_parsing()
