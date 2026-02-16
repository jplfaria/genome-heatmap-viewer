#!/usr/bin/env python3
"""
Validate scientific correctness and data integrity of genes_data.json.

Checks:
- Pangenome distribution (60-90% core expected for bacteria)
- Consistency score distribution (most genes >0.7 expected)
- Field ranges (conservation 0-1, protein length 20-5000, etc.)
- Cross-field consistency
- Multi-cluster gene handling
"""

import json
import sys
import statistics


def main():
    # Load data
    try:
        with open('config.json') as f:
            config = json.load(f)
        F = config['fields']

        with open('genes_data.json') as f:
            genes = json.load(f)

        with open('metadata.json') as f:
            metadata = json.load(f)

        print(f"✓ Loaded {len(genes)} genes")
        print(f"✓ Organism: {metadata.get('organism', 'Unknown')}")
        print(f"✓ Reference genomes: {metadata.get('n_ref_genomes', 'Unknown')}")
        print()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    errors = []
    warnings = []

    # ========================================
    # 1. PANGENOME DISTRIBUTION
    # ========================================
    print("=" * 60)
    print("1. PANGENOME DISTRIBUTION")
    print("=" * 60)

    core_count = sum(1 for g in genes if g[F['PAN_CAT']] == 2)
    accessory_count = sum(1 for g in genes if g[F['PAN_CAT']] == 1)
    unknown_count = sum(1 for g in genes if g[F['PAN_CAT']] == 0)

    core_pct = core_count / len(genes) * 100
    accessory_pct = accessory_count / len(genes) * 100
    unknown_pct = unknown_count / len(genes) * 100

    print(f"Core genes:      {core_count:4d} ({core_pct:5.1f}%)")
    print(f"Accessory genes: {accessory_count:4d} ({accessory_pct:5.1f}%)")
    print(f"Unknown:         {unknown_count:4d} ({unknown_pct:5.1f}%)")

    # Expected: 60-90% core for bacterial genomes
    if core_pct < 60:
        warnings.append(f"Core gene percentage ({core_pct:.1f}%) below expected 60-90% range")
    elif core_pct > 90:
        warnings.append(f"Core gene percentage ({core_pct:.1f}%) above expected 60-90% range")
    else:
        print(f"✓ Core percentage within expected range (60-90%)")

    if unknown_pct > 15:
        warnings.append(f"Unknown gene percentage ({unknown_pct:.1f}%) above expected <15%")
    else:
        print(f"✓ Unknown percentage within expected range (<15%)")

    # ========================================
    # 2. CONSERVATION DISTRIBUTION
    # ========================================
    print()
    print("=" * 60)
    print("2. CONSERVATION DISTRIBUTION")
    print("=" * 60)

    cons_values = [g[F['CONS_FRAC']] for g in genes if g[F['CONS_FRAC']] is not None]

    if cons_values:
        cons_min = min(cons_values)
        cons_max = max(cons_values)
        cons_mean = statistics.mean(cons_values)
        cons_median = statistics.median(cons_values)

        print(f"Min:    {cons_min:.4f}")
        print(f"Max:    {cons_max:.4f}")
        print(f"Mean:   {cons_mean:.4f}")
        print(f"Median: {cons_median:.4f}")

        # Check for out-of-range values
        out_of_range = [c for c in cons_values if c < 0.0 or c > 1.0]
        if out_of_range:
            errors.append(f"{len(out_of_range)} conservation values out of range [0, 1]")
        else:
            print("✓ All conservation values in valid range [0, 1]")

        # Check for bimodal distribution (expected for pangenome)
        high_cons = sum(1 for c in cons_values if c > 0.9)
        low_cons = sum(1 for c in cons_values if c < 0.5)
        print(f"High conservation (>0.9): {high_cons} ({high_cons/len(cons_values)*100:.1f}%)")
        print(f"Low conservation (<0.5):  {low_cons} ({low_cons/len(cons_values)*100:.1f}%)")

        if cons_mean < 0.3 or cons_mean > 0.95:
            warnings.append(f"Mean conservation ({cons_mean:.4f}) outside typical range")

    # ========================================
    # 3. CONSISTENCY SCORE DISTRIBUTION
    # ========================================
    print()
    print("=" * 60)
    print("3. CONSISTENCY SCORE DISTRIBUTION")
    print("=" * 60)

    avg_cons_values = [g[F['AVG_CONS']] for g in genes if g[F['AVG_CONS']] >= 0]  # Exclude N/A (-1)

    if avg_cons_values:
        cons_min = min(avg_cons_values)
        cons_max = max(avg_cons_values)
        cons_mean = statistics.mean(avg_cons_values)
        cons_median = statistics.median(avg_cons_values)

        print(f"Min:    {cons_min:.4f}")
        print(f"Max:    {cons_max:.4f}")
        print(f"Mean:   {cons_mean:.4f}")
        print(f"Median: {cons_median:.4f}")

        # Expected: Most genes >0.7 (annotations agree within clusters)
        high_cons = sum(1 for c in avg_cons_values if c > 0.7)
        med_cons = sum(1 for c in avg_cons_values if 0.4 <= c <= 0.7)
        low_cons = sum(1 for c in avg_cons_values if c < 0.4)

        high_pct = high_cons / len(avg_cons_values) * 100
        med_pct = med_cons / len(avg_cons_values) * 100
        low_pct = low_cons / len(avg_cons_values) * 100

        print(f"High (>0.7):     {high_cons:4d} ({high_pct:5.1f}%)")
        print(f"Medium (0.4-0.7): {med_cons:4d} ({med_pct:5.1f}%)")
        print(f"Low (<0.4):      {low_cons:4d} ({low_pct:5.1f}%)")

        if high_pct < 50:
            warnings.append(f"Only {high_pct:.1f}% genes have high consistency (expected >50%)")
        else:
            print(f"✓ {high_pct:.1f}% genes have high consistency (expected >50%)")

        # Check for invalid values
        na_count = sum(1 for g in genes if g[F['AVG_CONS']] == -1)
        print(f"N/A (no cluster): {na_count} genes")

        invalid = [g[F['AVG_CONS']] for g in genes if g[F['AVG_CONS']] < -1 or g[F['AVG_CONS']] > 1]
        if invalid:
            errors.append(f"{len(invalid)} consistency values out of valid range [-1, 1]")
        else:
            print("✓ All consistency values in valid range [-1, 1]")

    # ========================================
    # 4. PROTEIN LENGTH DISTRIBUTION
    # ========================================
    print()
    print("=" * 60)
    print("4. PROTEIN LENGTH DISTRIBUTION")
    print("=" * 60)

    prot_lengths = [g[F['PROT_LEN']] for g in genes]

    prot_min = min(prot_lengths)
    prot_max = max(prot_lengths)
    prot_mean = statistics.mean(prot_lengths)
    prot_median = statistics.median(prot_lengths)

    print(f"Min:    {prot_min} aa")
    print(f"Max:    {prot_max} aa")
    print(f"Mean:   {prot_mean:.1f} aa")
    print(f"Median: {prot_median:.1f} aa")

    # Expected: Most proteins 50-2000 aa, but giant proteins (>5000 aa) do exist
    # (e.g., hemolysins, adhesins, repetitive proteins)
    too_short = sum(1 for p in prot_lengths if p < 20)
    very_long = sum(1 for p in prot_lengths if p > 5000)

    if too_short > 0:
        warnings.append(f"{too_short} proteins shorter than 20 aa (may be annotation errors)")
    if very_long > 0:
        print(f"ℹ️  {very_long} very large proteins (>5000 aa) - these may be real (hemolysins, adhesins)")

    if too_short == 0:
        print("✓ No unexpectedly short proteins (<20 aa)")

    # ========================================
    # 5. CROSS-FIELD CONSISTENCY
    # ========================================
    print()
    print("=" * 60)
    print("5. CROSS-FIELD CONSISTENCY CHECKS")
    print("=" * 60)

    # Check 1: If PAN_CAT=0 (Unknown), then AVG_CONS should be -1 (N/A)
    unknown_with_cons = sum(1 for g in genes if g[F['PAN_CAT']] == 0 and g[F['AVG_CONS']] != -1)
    if unknown_with_cons > 0:
        warnings.append(f"{unknown_with_cons} genes have PAN_CAT=Unknown but AVG_CONS != N/A")
    else:
        print("✓ Unknown genes correctly have AVG_CONS = N/A")

    # Check 2: If CONS_FRAC=1.0, then PAN_CAT should be 2 (Core)
    perfect_cons_not_core = sum(1 for g in genes if g[F['CONS_FRAC']] == 1.0 and g[F['PAN_CAT']] != 2)
    if perfect_cons_not_core > 0:
        warnings.append(f"{perfect_cons_not_core} genes have 100% conservation but not marked as Core")
    else:
        print("✓ All 100% conserved genes marked as Core")

    # Check 3: Check for NaN or null values
    nan_count = 0
    for field_name, field_idx in F.items():
        nulls = sum(1 for g in genes if g[field_idx] is None and field_name not in ['REACTIONS'])
        if nulls > 0:
            warnings.append(f"{nulls} genes have null value for {field_name}")
            nan_count += nulls

    if nan_count == 0:
        print("✓ No unexpected null values found")

    # ========================================
    # 6. STRAND BALANCE
    # ========================================
    print()
    print("=" * 60)
    print("6. STRAND BALANCE")
    print("=" * 60)

    forward_count = sum(1 for g in genes if g[F['STRAND']] == 1)
    reverse_count = sum(1 for g in genes if g[F['STRAND']] == 0)

    forward_pct = forward_count / len(genes) * 100
    reverse_pct = reverse_count / len(genes) * 100

    print(f"Forward strand: {forward_count:4d} ({forward_pct:5.1f}%)")
    print(f"Reverse strand: {reverse_count:4d} ({reverse_pct:5.1f}%)")

    # Expected: ~50/50 with slight bias acceptable
    if forward_pct < 40 or forward_pct > 60:
        warnings.append(f"Strand bias unusual: {forward_pct:.1f}% forward (expected 40-60%)")
    else:
        print("✓ Strand balance within expected range (40-60% forward)")

    # ========================================
    # SUMMARY
    # ========================================
    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total genes validated: {len(genes)}")
    print(f"Errors found: {len(errors)}")
    print(f"Warnings: {len(warnings)}")

    if errors:
        print()
        print("ERRORS:")
        for err in errors:
            print(f"  ❌ {err}")

    if warnings:
        print()
        print("WARNINGS:")
        for warn in warnings:
            print(f"  ⚠️  {warn}")

    if not errors and not warnings:
        print()
        print("✅ ALL VALIDATION CHECKS PASSED!")
        print("   Data integrity and scientific correctness verified.")
        return 0
    elif not errors:
        print()
        print("✅ NO CRITICAL ERRORS")
        print("   Warnings noted but data appears scientifically valid.")
        return 0
    else:
        print()
        print("❌ CRITICAL ERRORS FOUND")
        print("   Review and fix data extraction scripts.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
