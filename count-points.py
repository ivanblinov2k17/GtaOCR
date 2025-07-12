import os
o = open('report.txt','w', encoding="utf-8")

main_folder_path = 'E:\\samp_screens\\5-6'
# main_folder_path = 'output_images'

folders = ['heal', 'reanimation', 'vaccine']
locations = ['ELSH', 'Sandy-Shores', 'Paleto-Bay']
reanimation_locations = ['City', 'NotCity']
timestamp = ['Day', 'Night']

# Scoring rules
heal_scores = {
    'ELSH': 1,
    'Sandy-Shores': 2,
    'Paleto-Bay': 2,
}

vaccine_scores = {
    'ELSH': 3,
    'Sandy-Shores': 5,
    'Paleto-Bay': 5,
}

reanimation_scores = {
    ('City', 'Day'): 3,
    ('NotCity', 'Day'): 4,
    ('City', 'Night'): 5,
    ('NotCity', 'Night'): 6,
}

total_score = 0
reanimation_score = 0
detailed_report = []

# Ask the user to enter the target total score
while True:
    try:
        target_total_score = int(input("🎯 Enter your target total score: "))
        if target_total_score > 0:
            break
        else:
            print("Please enter a positive number.", file=o)
    except ValueError:
        print("Invalid input. Please enter a number.", file=o)


# Count and score 'heal' and 'vaccine'
for category in ['heal', 'vaccine']:
    for loc in locations:
        folder_path = os.path.join(main_folder_path, category, loc)
        if os.path.exists(folder_path):
            file_count = len([
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ])
            per_file_score = (heal_scores if category == 'heal' else vaccine_scores)[loc]
            score = file_count * per_file_score
            total_score += score
            detailed_report.append(
                f"{category.capitalize()} – {loc}: {file_count} files × {per_file_score} pts = {score}"
            )

# Count and score 'reanimation'
for loc in reanimation_locations:
    for time in timestamp:
        folder_path = os.path.join(main_folder_path, 'reanimation', loc, time)
        if os.path.exists(folder_path):
            file_count = len([
                f for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f))
            ])
            per_file_score = reanimation_scores.get((loc, time), 0)
            score = file_count * per_file_score
            reanimation_score += score
            total_score += score
            detailed_report.append(
                f"Reanimation – {loc}/{time}: {file_count} files × {per_file_score} pts = {score}"
            )

# Print the report
print("\nDETAILED REPORT:", file=o)
print("----------------------------", file=o)
for line in detailed_report:
    print(line)
print("----------------------------", file=o)
print(f"TOTAL SCORE: {total_score}", file=o)
if total_score > 0:
    percent = (reanimation_score / total_score) * 100
    print(f"Reanimation % of total: {reanimation_score} pts → {percent:.2f}%", file=o)
    # Check if reanimation meets 70% goal
    target_percentage = 70
    if percent < target_percentage:
        # How many reanimation points needed to reach 70%
        required_points = (target_percentage / 100 * total_score - reanimation_score) / (1 - target_percentage / 100)
        required_points = max(0, int(required_points) + 1)  # round up
        print(f"⚠ To reach {target_percentage}% reanimation score, you need at least {required_points} more reanimation points.", file=o)
    else:
        print(f"✅ Reanimation goal of {target_percentage}% achieved!", file=o)

    # Part 1 – Target total score
    if total_score < target_total_score:
        more_needed = target_total_score - total_score
        print(f"📈 You need {more_needed} more points to reach the target total score of {target_total_score}.", file=o)
    else:
        print(f"✅ Total score target of {target_total_score} reached.", file=o)

    # Part 2 – How many non-reanimation points to delete to reach 70%
    non_reanimation_score = total_score - reanimation_score
    required_ratio = 0.7

    # Solve for how many non-reanimation points to remove
    # such that: reanimation_score / (total_score - x) >= 0.7
    import math
    max_removable = non_reanimation_score
    min_needed_removal = math.ceil(total_score - (reanimation_score / required_ratio))

    if reanimation_score / total_score >= required_ratio:
        print(f"✅ Current reanimation score already meets {int(required_ratio * 100)}% threshold.", file=o)
    elif min_needed_removal <= max_removable:
        print(f"🗑️ You can delete at least {min_needed_removal} non-reanimation points ({min_needed_removal} worth of screenshots)", file=o)
        print(f"   to meet the {int(required_ratio * 100)}% reanimation threshold.", file=o)
    else:
        print(f"❌ You cannot reach {int(required_ratio * 100)}% reanimation threshold by deleting screenshots alone.", file=o)



else:
    print("No files found. Total score is 0.", file=o)
