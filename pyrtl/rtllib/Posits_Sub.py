import pyrtl
from pyrtl.corecircuits import shift_left_logical, shift_right_logical
import math

def create_posit_subtractor_n_es(n, es):
    """
    Generates a PyRTL hardware design for a posit subtractor.

    This function is a factory that creates a subtractor circuit customized
    for the given posit configuration (n, es).

    Args:
        n (int): The total number of bits in the posit format.
        es (int): The number of exponent bits in the posit format.
    """
    pyrtl.reset_working_block()

    # --- Derived Parameters ---
    # These widths are calculated to be large enough for any valid n, es.
    # Width for counters/lengths that go up to n (e.g., run_len).
    n_bits_width = math.ceil(math.log2(n + 1)) if n > 0 else 1
    # Width for the regime value 'k'. Needs to be signed and can range approx -n to +n.
    k_width = n_bits_width + 2
    # Width for the scale value (k << es + e).
    scale_width = k_width + es
    # Width for the offset (difference between two scales).
    offset_width = scale_width + 1
    # A generous internal width for fraction arithmetic to prevent overflow during shifts.
    # The maximum shift can be large, so 3*n provides a safe margin.
    internal_width = 3 * n

    # --- Inputs / Outputs ---
    a = pyrtl.Input(bitwidth=n, name='a')
    b = pyrtl.Input(bitwidth=n, name='b')
    result = pyrtl.Output(bitwidth=n, name='result')

    # --- Decode Posit ---
    def decode_posit(x):
        """ Decodes a posit into its sign, k, exponent, and fraction components. """
        is_zero = (x == 0)
        is_nar = (x == (1 << (n - 1)))

        sign = x[n - 1]
        
        # Invert bits if sign is 1 (two's complement representation of posits)
        x_abs = pyrtl.select(sign, ~x + 1, x)

        regime_bits = x_abs[0:n-1]
        
        # Find the end of the regime
        # First bit determines if regime is 1s or 0s
        regime_term_bit = ~regime_bits[n-2]
        
        run_len = pyrtl.WireVector(bitwidth=n_bits_width)
        
        # Priority encoder to find first regime terminating bit
        found = pyrtl.Const(0, 1)
        for i in reversed(range(n-1)):
            is_terminator = (regime_bits[i] == regime_term_bit)
            with pyrtl.conditional_assignment:
                with ~found & is_terminator:
                    run_len |= (n-2-i)
            found = found | is_terminator

        with pyrtl.conditional_assignment:
            with ~found: # All bits are the same
                run_len |= n-1


        regime_val = pyrtl.select(regime_term_bit, -run_len, run_len - 1)
        k = pyrtl.as_signed(regime_val)
        k.bitwidth = k_width
        
        # Calculate remaining bits after regime
        rem_len = n - 2 - run_len
        
        # Extract exponent and fraction
        exp = pyrtl.WireVector(bitwidth=es)
        frac_max_len = n - 2 - es # Theoretical max
        frac = pyrtl.WireVector(bitwidth=max(1, frac_max_len))

        with pyrtl.conditional_assignment:
            with rem_len >= es:
                exp_and_frac = x_abs << (run_len + 2)
                exp |= exp_and_frac[n-1-es:n-1]
                frac_len = rem_len - es
                frac_shifted = exp_and_frac << es
                frac |= frac_shifted[n-1-frac_max_len: n-1] if frac_max_len > 0 else 0
            with rem_len < es:
                exp_and_frac = x_abs << (run_len + 2)
                exp |= exp_and_frac[n-1-rem_len:n-1] << (es - rem_len) if rem_len > 0 else 0
                frac_len = 0
                frac |= 0

        # Handle special cases at the end
        with pyrtl.conditional_assignment:
            with is_zero:
                k |= 0
                exp |= 0
                frac |= 0
            with is_nar:
                # NaR doesn't have a valid k, exp, or frac
                pass

        return sign, k, exp, frac, is_zero, is_nar


    # --- Add the hidden bit to the fraction ---
    def frac_with_hidden_one(frac):
        """ Prepends the implicit '1' bit to the fraction for calculations. """
        # The fraction is always prepended with a '1' unless the value is zero/NaR
        hidden_bit = pyrtl.Const(1, bitwidth=1)
        # Combine with the explicit fraction bits.
        full_frac = pyrtl.concat(hidden_bit, frac)
        # Zero-extend to the internal working width.
        return pyrtl.concat(pyrtl.Const(0, bitwidth=internal_width - full_frac.bitwidth), full_frac)


    # --- Main Posit Subtractor Logic ---
    def posit_sub(a_in, b_in):
        """ Top-level function for the subtraction a - b. """
        s1, k1, e1, f1, is_a_zero, is_a_nar = decode_posit(a_in)
        s2_orig, k2, e2, f2, is_b_zero, is_b_nar = decode_posit(b_in)
        
        # For subtraction a - b, we calculate a + (-b).
        # The sign of -b is ~s2_orig.
        s2 = ~s2_orig

        # Handle special cases immediately
        nar_result = pyrtl.Const((1 << (n - 1)), bitwidth=n)
        with pyrtl.conditional_assignment:
            with is_a_nar | is_b_nar:
                return nar_result
            with is_a_zero:
                return pyrtl.concat(~s2_orig, b_in[0:n-1]) # return -b
            with is_b_zero:
                return a_in # return a

        # Effective operation is addition if signs are the same, subtraction otherwise
        op_is_add = (s1 == s2)

        # Calculate the total scale for each posit
        scale1 = (pyrtl.as_signed(k1) << es) + pyrtl.as_signed(e1)
        scale2 = (pyrtl.as_signed(k2) << es) + pyrtl.as_signed(e2)
        scale1.bitwidth = scale_width
        scale2.bitwidth = scale_width

        # Get fractions with the hidden bit prepended
        frac1_full = frac_with_hidden_one(f1)
        frac2_full = frac_with_hidden_one(f2)

        # Align fractions by shifting the one with the smaller scale
        offset = pyrtl.as_signed(scale1) - pyrtl.as_signed(scale2)
        offset.bitwidth = offset_width
        
        shifted1 = pyrtl.WireVector(bitwidth=internal_width)
        shifted2 = pyrtl.WireVector(bitwidth=internal_width)
        result_scale = pyrtl.WireVector(bitwidth=scale_width)
        
        offset_is_neg = offset[-1]
        abs_offset = pyrtl.select(offset_is_neg, -offset, offset)

        with pyrtl.conditional_assignment:
            with offset_is_neg: # scale1 < scale2, shift frac1 right
                shifted1 |= frac1_full >> abs_offset
                shifted2 |= frac2_full
                result_scale |= scale2
            with ~offset_is_neg: # scale1 >= scale2, shift frac2 right
                shifted1 |= frac1_full
                shifted2 |= frac2_full >> abs_offset
                result_scale |= scale1
        
        # Perform addition or subtraction on aligned fractions
        mag_result = pyrtl.WireVector(bitwidth=internal_width)
        result_sign = pyrtl.WireVector(bitwidth=1)
        
        with pyrtl.conditional_assignment:
            with op_is_add:
                mag_result |= shifted1 + shifted2
                result_sign |= s1
            with ~op_is_add:
                # Subtraction of magnitudes
                with shifted1 >= shifted2:
                    mag_result |= shifted1 - shifted2
                    result_sign |= s1
                with shifted1 < shifted2:
                    mag_result |= shifted2 - shifted1
                    result_sign |= s2

        is_result_zero = (mag_result == 0)

        # Normalize the result: find the MSB to adjust scale and fraction
        msb_pos = pyrtl.WireVector(bitwidth=n_bits_width)
        found_msb = pyrtl.Const(0, 1)
        for i in reversed(range(internal_width)):
            is_set = mag_result[i]
            with pyrtl.conditional_assignment:
                with ~found_msb & is_set:
                    msb_pos |= i
            found_msb = found_msb | is_set
        
        # The alignment point of the hidden bit was at frac_max_len.
        # It is now at msb_pos. The scale must be adjusted by the difference.
        scale_adjustment = pyrtl.as_signed(msb_pos) - (max(1, frac_max_len) + 1)
        final_scale = pyrtl.as_signed(result_scale) + scale_adjustment
        
        # --- Re-encode into Posit Format ---
        # This is a simplified re-encoding and does not include rounding logic (e.g., round-to-nearest-even)
        
        final_k_signed = pyrtl.as_signed(final_scale) >> es
        final_e = final_scale & ((1 << es) - 1)
        
        # Build the regime
        k_is_neg = final_k_signed[-1]
        abs_k = pyrtl.select(k_is_neg, -final_k_signed, final_k_signed)
        
        run_len = pyrtl.select(k_is_neg, abs_k, abs_k + 1)
        
        regime = pyrtl.WireVector(n-1)
        with pyrtl.conditional_assignment:
            with k_is_neg: # Regime of 0s followed by a 1
                 # e.g., if run_len = 3, we want ...0001...
                 regime |= pyrtl.Const(1) << (n - 2 - run_len)
            with ~k_is_neg: # Regime of 1s followed by a 0
                 # e.g., if run_len = 3, we want ...1110...
                 regime |= ((pyrtl.Const(1) << run_len) -1 ) << (n-1-run_len)
        
        # Remove the new hidden bit from the fraction
        frac_to_encode = mag_result << (internal_width - msb_pos)
        
        # Combine exponent and fraction
        exp_and_frac = pyrtl.concat(final_e, frac_to_encode)
        
        # Number of available bits after the regime
        rem_bits = n - 2 - run_len
        
        # Combine all parts
        unsigned_result = pyrtl.WireVector(n-1)
        with pyrtl.conditional_assignment:
            with rem_bits > 0:
                # Shift exp+frac into position
                shifted_exp_frac = exp_and_frac >> (exp_and_frac.bitwidth - rem_bits)
                unsigned_result |= regime | shifted_exp_frac
            with rem_bits <= 0:
                unsigned_result |= regime

        # Two's complement the result if the sign is negative
        final_unsigned = pyrtl.concat(pyrtl.Const(0, 1), unsigned_result)
        final_signed = pyrtl.select(result_sign, -final_unsigned, final_unsigned)

        #handle the the edge case of 1|0 and 0|1
        # Final result with special case handling
        final_posit = pyrtl.select(
            is_result_zero,
            truecase=pyrtl.Const(0, bitwidth=n),
            falsecase=final_signed
        )
        return final_posit

    # --- Instantiate the subtractor circuit ---
    result <<= posit_sub(a, b)
    return pyrtl.working_block()

# --- Simulation and Test ---
if __name__ == '__main__':
    # --- Configuration ---
    # You can change these values to test different posit formats
    N_BITS = 8
    ES_BITS = 1

    print(f"--- Testing Posit<{N_BITS}, {ES_BITS}> Subtractor ---")
    
    # Create the hardware design for the specified configuration
    # This needs to be done before any simulation setup
    try:
        posit_sub_block = create_posit_subtractor_n_es(n=N_BITS, es=ES_BITS)
    except pyrtl.PyrtlError as e:
        print(f"Error creating PyRTL block: {e}")
        print("Please ensure n and es values are valid (e.g., n > es + 2)")
        exit()


    # Setup simulation
    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace, block=posit_sub_block)

    # --- Test Case ---
    # a = 0b01000100 -> Posit<8,1> represents 0.5
    # b = 0b01101000 -> Posit<8,1> represents 4.0
    # a - b = 0.5 - 4.0 = -3.5
    # -3.5 in Posit<8,1> is approximately 0b10011100 (which is the encoding for -4.0, the closest value)
    # The exact value -3.5 cannot be represented. Let's test with representable values.
    #
    # Test 2: 4.0 - 0.5 = 3.5
    # a = 4.0 -> 0b01101000
    # b = 0.5 -> 0b01000100
    # result should be 3.5 -> approx 0b01100110 (which is 3.0, the nearest value)
    
    a_val = 0b01101000 # 4.0
    b_val = 0b01000100 # 0.5
    
    # Run the simulation step
    sim.step({'a': a_val, 'b': b_val})

    # Inspect the simulation output
    result_val = sim.inspect('result')

    print(f"\nInput 'a'    : {a_val:0{N_BITS}b} (Represents ~4.0)")
    print(f"Input 'b'    : {b_val:0{N_BITS}b} (Represents 0.5)")
    print(f"Result a-b   : {result_val:0{N_BITS}b} (Represents ~3.0)")
    print(f"Expected approx: {0b01100110:0{N_BITS}b}")