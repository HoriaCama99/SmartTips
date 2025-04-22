import streamlit as st
import json
import random # To simulate different profiles
import time   # To simulate delay

st.set_page_config(layout="wide", page_title="Energy Tips Advisor", page_icon="💡")

st.title("💡 Personalized Energy Saving Tips Advisor")

# --- Data Loading ---
@st.cache_data
def load_tips(filepath="Xcel Tips - 250313.json"):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            st.error(f"Error: JSON structure in {filepath} is not a list of objects.")
            return []
        return data
    except FileNotFoundError:
        st.error(f"Error: The file {filepath} was not found.")
        return []
    except json.JSONDecodeError:
        st.error(f"Error: Could not decode JSON from {filepath}.")
        return []

tips_data = load_tips()

if not tips_data:
    st.warning("Tip data could not be loaded. Please check the JSON file.")
    st.stop()

# --- Placeholder Profile Simulation ---
def get_profile_for_custid(custid):
    """Simulates fetching a customer profile based on custid."""
    # In reality, this would query your NILM output database/API
    seed = hash(custid) # Use custid hash for pseudo-randomness
    random.seed(seed)
    time.sleep(0.5) # Simulate network delay

    profile = {
        "custid": custid,
        "👤 User Type": random.choice(["residential", "commercial", "res&com"]),
        "📍 Area Type": random.choice(["Favorable", "Unfavorable", "Standard"]),
        "🧊 Freezer": random.choice(["Yes", "No"]),
        "🍽️ Dishwasher": random.choice(["Yes", "No"]),
        "💨 Dryer": random.choice(["Yes", "No"]),
        "🧺 Washer": random.choice(["Yes", "No"]),
        "🏊 Pool": random.choice(["Yes", "No"]),
        "🛁 Hot Tub": random.choice(["Yes", "No"]),
        "🔥 Pool Heater Months": random.randint(0, 6) if random.choice([True, False]) else 0,
        "💲 Rate Plan": random.choice(["TOU", "Standard", "EV Rate"]),
        "🧱 Insulation Pre 1992": random.choice([True, False]),
        "🌡️ Programmable Thermostat": random.choice(["Yes", "No"]),
        "💡 CFLs/LEDs": random.choice(["All", "Some", "None"]),
        "❄️ Cooling System": random.choice(["Yes", "No"]),
        "⚡ Electric Water Heater": random.choice(["Yes", "No"]),
        "🌬️ Ducts": random.choice(["No Ducts", "Standard Ducts", "Leaky Ducts"])
    }
    # Map internal names used by rules to the display names
    profile["user_type"] = profile["👤 User Type"]
    profile["Area Type"] = profile["📍 Area Type"]
    profile["Freezer"] = profile["🧊 Freezer"]
    profile["Dishwasher"] = profile["🍽️ Dishwasher"]
    profile["Dryer"] = profile["💨 Dryer"]
    profile["Washer"] = profile["🧺 Washer"]
    profile["Pool"] = profile["🏊 Pool"]
    profile["Hot Tub"] = profile["🛁 Hot Tub"]
    profile["Pool Heater"] = profile["🔥 Pool Heater Months"] # Map for rule evaluation
    profile["Rate Plan"] = profile["💲 Rate Plan"]
    profile["Insulation Pre 1992"] = profile["🧱 Insulation Pre 1992"]
    profile["Programmable Thermostat"] = profile["🌡️ Programmable Thermostat"]
    profile["CFLs"] = profile["💡 CFLs/LEDs"] # Assuming CFLs rule maps to this
    profile["Cool"] = profile["❄️ Cooling System"]
    profile["Water Heater Electric"] = profile["⚡ Electric Water Heater"]
    profile["Ducts"] = profile["🌬️ Ducts"]
    return profile

# --- Rule Evaluation Logic ---
def get_appliance_from_rule(rule_str):
    """Attempts to infer the primary appliance/category from a rule string."""
    rule_str = rule_str.strip()
    if rule_str == "Always":
        return "General"
    
    # Simple extraction based on the first word after "If"
    # Covers rules like "If Freezer = ...", "If Pool = ...", "If Rate Plan = ..."
    if rule_str.startswith("If "):
        parts = rule_str[3:].split()
        if parts:
            # Consider known multi-word entities first
            if rule_str.startswith("If Pool Heater "):
                 return "Pool Heater"
            if rule_str.startswith("If Water Heater "):
                 return "Water Heater"
            if rule_str.startswith("If Rate Plan "):
                 return "Rate Plan" # Categorize as non-appliance general
            if rule_str.startswith("If Insulation Pre "):
                 return "Insulation" # Categorize as non-appliance general
            # Default to the first word if it seems like an appliance/attribute
            first_word = parts[0]
            # Add more known appliance/attribute names here if needed
            known_entities = ["Freezer", "Refrigerator", "Washer", "Dishwasher", "Dryer", 
                              "Pool", "Hot Tub", "Thermostat", "CFLs", "Cool", "Ducts", "Heater"]
            if first_word in known_entities:
                 return first_word
            # Fallback for other "If" rules - could be general or unclassifiable
            return "General" # Or perhaps None if we want to be stricter
            
    # Complex rules or unknown format
    if rule_str == "If match on All five Keys":
         # This rule applies to specific equipment based on other fields, 
         # but we can't easily map it here without knowing the context.
         # Let's classify as General for button purposes, filtering happens later.
         return "General" 
         
    return "General" # Default for any other unparsed rules

def get_tip_suitability(tip):
    """MOCKUP: Guesses tip suitability for Favorable/Unfavorable areas."""
    headline = tip.get("headline", "").lower()
    description = tip.get("description", "").lower()
    text_content = headline + " " + description
    rowid = tip.get("rowid")

    # High-cost / Replacement / Installation oriented tips -> Favorable?
    favorable_keywords = ["replace", "install new", "upgrade", "geothermal", "solar", "investment", "remodel", "purchase", "high efficiency", "energy star model"]
    if any(keyword in text_content for keyword in favorable_keywords):
        # Exceptions: low-cost replacements
        if "light bulbs" in text_content or "led" in text_content or "faucet aerators" in text_content or "shower heads" in text_content:
            return "All"
        if rowid in [94, 19, 330]: # Programmable thermostat, Smart strips - maybe affordable?
             return "All"
        return "Favorable"

    # Low-cost / Behavioral / Maintenance / Repair oriented tips -> Unfavorable / All?
    unfavorable_keywords = ["unplug", "turn off", "clean", "maintain", "repair", "seal", "fix leaky", "lower setting", "reduce", "shorten", "check", "schedule", "wash full loads", "use cold water", "cover", "settings", "timer"]
    if any(keyword in text_content for keyword in unfavorable_keywords):
        # These seem suitable for everyone
        return "All"
    
    # Specific checks (examples)
    if rowid in [161, 162, 163]: # Mold/poison/pest remediation - essential, likely Unfavorable targeted
         return "Unfavorable"
    if "mobile home" in text_content: # Explicit mention
         return "Unfavorable"

    # Default: Assume suitable for All if no strong indicator found
    return "All"

def evaluate_rule(rule_str, profile):
    """Evaluates if a tip's rule applies to the customer profile."""
    rule_str = rule_str.strip()
    if rule_str == "Always":
        return True

    if rule_str.startswith("If "):
        parts = rule_str[3:].split()
        if len(parts) >= 3:
            attribute = parts[0]
            potential_attribute = attribute
            idx = 1
            # Handle multi-word attributes based on keys *present* in the profile dict
            while idx < len(parts) - 1 and (potential_attribute + " " + parts[idx]) in profile:
                 potential_attribute += " " + parts[idx]
                 idx += 1
            
            if potential_attribute in profile:
                 attribute = potential_attribute
                 operator_start_index = idx
            elif attribute not in profile:
                return False # Attribute not found
            else:
                 operator_start_index = 1 # Single word attribute
            
            if attribute not in profile:
                return False # Should not happen if logic above is correct, but safe check
                
            profile_value = profile[attribute]
            
            if operator_start_index >= len(parts):
                return False # Incomplete rule structure
                
            operator = parts[operator_start_index]
            value_parts_start_index = operator_start_index + 1
            
            potential_operator = operator
            idx = operator_start_index + 1
            # Handle multi-word operators 
            while idx < len(parts) -1 and (potential_operator + " " + parts[idx]) in ["Not Equal", "Greater than", "Not Equal to"]:
                potential_operator += " " + parts[idx]
                idx += 1
            
            # Normalize operator names
            if potential_operator in ["Not Equal", "Not Equal to"]:
                operator = "Not Equal"
                value_parts_start_index = idx
            elif potential_operator == "Greater than":
                 operator = "Greater than"
                 value_parts_start_index = idx
            elif operator not in ["="]:
                return False # Unsupported operator

            if value_parts_start_index >= len(parts):
                 return False # Missing value
            
            value_str = " ".join(parts[value_parts_start_index:]).strip('"')

            try:
                if operator == "=":
                    # Special check for boolean-like profile values
                    if isinstance(profile_value, bool):
                        return profile_value == (value_str.lower() == 'yes' or value_str.lower() == 'true')
                    return str(profile_value) == value_str
                elif operator == "Not Equal":
                     if isinstance(profile_value, bool):
                         return profile_value != (value_str.lower() == 'yes' or value_str.lower() == 'true')
                     return str(profile_value) != value_str
                elif operator == "Greater than":
                     # Attempt numeric comparison first
                     return float(profile_value) > float(value_str)
            except (ValueError, TypeError):
                 # Comparison failed (likely type mismatch)
                 return False 
            except Exception as e:
                 # Log unexpected errors during evaluation
                 st.warning(f"Internal error evaluating rule '{rule_str}': {e}")
                 return False
            
            return False # Fallthrough if operator logic not met
        else:
             return False # "If" rule doesn't have enough parts

    # Handle specific boolean-like rules
    if rule_str == "If Insulation Pre 1992":
         # Check if the key exists and is True
         return profile.get("Insulation Pre 1992", False) is True
    # Add more specific rule handlers if needed based on JSON analysis

    # Handle complex rules (placeholder)
    if rule_str == "If match on All five Keys":
        # Needs definition based on which keys and how they map to profile
        # Example check (adjust based on actual logic needed):
        # tip_fuel = tip.get("fuel")
        # tip_sub1 = tip.get("sub_id1")
        # tip_sub2 = tip.get("sub_id2")
        # tip_utype = tip.get("user_type")
        # profile_fuel = profile.get("PrimaryFuel") # Hypothetical profile key
        # profile_equip_type = profile.get("EquipmentType") # Hypothetical
        # return (tip_fuel == profile_fuel and ...)
        return False # Keep as False until defined

    # Default: Unhandled rule format or rule evaluates to false
    return False

# --- Session State Initialization ---
def init_session_state():
    # Initialize keys if they don't exist
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("current_custid", None)
    st.session_state.setdefault("customer_profile", None)
    st.session_state.setdefault("processing", False)
    st.session_state.setdefault("detected_appliances", None) # New state
    st.session_state.setdefault("selected_appliance", None) # New state

init_session_state() # Ensure state is initialized on each run

# --- Sidebar ---
st.sidebar.title("👤 Customer Profile")
profile_placeholder = st.sidebar.empty()

# Display profile info if available in state
if st.session_state.customer_profile:
    with profile_placeholder.container():
        custid = st.session_state.customer_profile.get("custid", "N/A")
        st.subheader(f"Details for {custid}")
        # Filter out internal mapping keys before displaying JSON
        display_profile = {k: v for k, v in st.session_state.customer_profile.items() if k not in [
            "custid", "user_type", "Freezer", "Dishwasher", "Dryer", "Washer", "Pool", 
            "Hot Tub", "Pool Heater", "Rate Plan", "Insulation Pre 1992", 
            "Programmable Thermostat", "CFLs", "Cool", "Water Heater Electric", "Ducts"
        ]}
        if display_profile:
             st.json(display_profile, expanded=True)
             st.caption("(Simulated data based on ID)")
        else:
             st.info("No displayable profile data found.")
else:
    profile_placeholder.info("Enter a Customer ID in the chat to see the simulated profile here.")

# New Chat Button
st.sidebar.divider()
if st.sidebar.button("🔄 Start New Chat", use_container_width=True):
    # Clear relevant session state keys
    st.session_state.messages = []
    st.session_state.current_custid = None
    st.session_state.customer_profile = None # Clear profile display
    st.session_state.processing = False
    profile_placeholder.info("Enter a Customer ID in the chat to see the simulated profile here.") # Reset sidebar message
    st.rerun() # Rerun to reflect the cleared state

# --- Chat Processing Function ---
def process_custid_input(custid):
    """Handles the logic for fetching profile and detecting appliances."""
    if st.session_state.processing: 
        st.warning("Already processing a request.")
        return 
        
    st.session_state.processing = True
    st.session_state.current_custid = custid
    st.session_state.selected_appliance = None # Reset selected appliance
    st.session_state.detected_appliances = None # Reset detected appliances
    
    # Append user message immediately
    st.session_state.messages.append({"role": "user", "content": f"Get tips for {custid}"})
    # Rerun to show the user message and trigger the processing block below
    st.rerun() 

# --- Main App Flow ---

# This block executes *after* a rerun triggered by process_custid_input
if st.session_state.processing and st.session_state.current_custid:
    custid_to_process = st.session_state.current_custid
    assistant_response_content = None
    detected_appliances_list = ["General"] # Always include General
    
    # Display spinner within the assistant's message context
    with st.chat_message("assistant"):
        with st.spinner(f"Analyzing profile for {custid_to_process}..."):
            try:
                customer_profile = get_profile_for_custid(custid_to_process)
                st.session_state.customer_profile = customer_profile # Update state

                # --- Detect Appliances/Categories based on Profile --- 
                # Define profile keys that indicate appliance presence (adjust as needed)
                appliance_presence_keys = {
                    "Freezer": "🧊 Freezer",
                    "Dishwasher": "🍽️ Dishwasher",
                    "Dryer": "💨 Dryer",
                    "Washer": "🧺 Washer",
                    "Pool": "🏊 Pool",
                    "Hot Tub": "🛁 Hot Tub",
                    "Pool Heater": "🔥 Pool Heater Months", # Check if months > 0 ?
                    # Add others if relevant rules exist
                }
                for appliance, profile_key in appliance_presence_keys.items():
                    profile_value = customer_profile.get(profile_key)
                    # Simple check for "Yes" or numeric > 0 (customize logic as needed)
                    is_present = False
                    if isinstance(profile_value, str) and profile_value.lower() == "yes":
                         is_present = True
                    elif isinstance(profile_value, (int, float)) and profile_value > 0:
                         is_present = True # e.g., Pool Heater Months > 0
                    # Add boolean True checks if profile uses booleans
                    # elif isinstance(profile_value, bool) and profile_value is True:
                    #      is_present = True
                        
                    if is_present:
                         if appliance not in detected_appliances_list:
                              detected_appliances_list.append(appliance)
               
                # Add other categories based on profile attributes used in rules
                if customer_profile.get("💲 Rate Plan") == "TOU":
                     if "Rate Plan" not in detected_appliances_list:
                          detected_appliances_list.append("Rate Plan")
                if customer_profile.get("🧱 Insulation Pre 1992") is True:
                     if "Insulation" not in detected_appliances_list:
                          detected_appliances_list.append("Insulation")
                # ... add more checks for Thermostat, CFLs, Cool, Ducts etc. if desired ...
               
                st.session_state.detected_appliances = sorted(detected_appliances_list)
               
                # Prepare response: Prompt to select an appliance
                assistant_response_content = f"OK, I've analyzed the profile for {custid_to_process}. Based on the simulation, I can offer tips in these categories. Please select one:"

            except Exception as e:
                 st.error(f"An error occurred processing ID {custid_to_process}: {e}", icon="🚨")
                 assistant_response_content = f"Sorry, I couldn't process the request for {custid_to_process}. Please try again."
                 st.session_state.detected_appliances = None # Ensure buttons don't show on error

    # Add the prompt message to history
    st.session_state.messages.append({"role": "assistant", "content": assistant_response_content})
    
    # Reset processing flags and trigger final rerun to display results/buttons
    st.session_state.processing = False
    st.session_state.current_custid = None 
    st.rerun()

# --- Display UI Elements (Welcome/History/Input/Buttons/Tips) ---

# Display Welcome and Example Buttons ONLY if chat is empty AND not processing
if not st.session_state.messages and not st.session_state.processing:
    st.info("👋 Welcome! Enter a Customer ID below, or try one of these examples:")
    cols = st.columns(3)
    example_ids = ["CUST101", "BIZ456", "HOME789"]
    for i, example_id in enumerate(example_ids):
        # Use a unique key for each button
        if cols[i].button(f"Get tips for {example_id}", key=f"example_{example_id}", use_container_width=True):
            process_custid_input(example_id)

# Display Chat History Messages
message_container = st.container() # Use a container for messages
with message_container:
    for message in st.session_state.messages:
        role = message.get("role", "assistant") # Default role if missing
        content = message.get("content")
        
        with st.chat_message(role):
            if isinstance(content, list):
                # This case should ideally not happen with the new flow, but handle defensively
                 st.warning("Unexpected list content found in message history.")
            elif isinstance(content, str):
                st.markdown(content)
            else:
                 st.warning("Skipping message with unknown content type.")

# Display Appliance Buttons if detected and none selected yet
if st.session_state.detected_appliances and not st.session_state.selected_appliance:
    st.write("**Tip Categories:**") # Header for buttons
    cols = st.columns(len(st.session_state.detected_appliances)) 
    for i, appliance_name in enumerate(st.session_state.detected_appliances):
        # Use appliance name in button key for uniqueness
        if cols[i].button(f"{appliance_name} Tips", key=f"btn_{appliance_name}", use_container_width=True):
            st.session_state.selected_appliance = appliance_name
            # Clear previously displayed tips if any (optional)
            # st.session_state.appliance_specific_tips = [] 
            st.rerun()

# Display Tips for Selected Appliance (with added suitability filtering)
if st.session_state.selected_appliance and st.session_state.customer_profile:
    selected = st.session_state.selected_appliance
    profile = st.session_state.customer_profile
    customer_area_type = profile.get("Area Type", "Standard") # Get customer's area type
    
    st.subheader(f"✨ Tips for: {selected} (Area: {customer_area_type})") # Show area type
    
    # Filter tips based on selected appliance AND profile
    appliance_specific_tips = []
    with st.spinner(f"Finding initial {selected} tips..."):
        for tip in tips_data:
            rule = tip.get("rule", "")
            if evaluate_rule(rule, profile): # Check profile match
                 tip_category = get_appliance_from_rule(rule)
                 if tip_category == selected: # Check selected appliance match
                      appliance_specific_tips.append(tip)
                     
    # --- Apply SECOND filter based on Area Type Suitability ---
    final_display_tips = []
    with st.spinner(f"Filtering tips based on area suitability ({customer_area_type})..."):
        if not appliance_specific_tips: # Skip if no tips passed first filter
            pass
        else:
             for tip in appliance_specific_tips:
                 tip_suitability = get_tip_suitability(tip) # Use the MOCKUP function
                 # Keep tip if suitable for All or matches customer's area type
                 if tip_suitability == "All" or tip_suitability == customer_area_type:
                      final_display_tips.append(tip)

    # Display the FINAL filtered tips
    if final_display_tips:
        st.success(f"Found {len(final_display_tips)} specific tip(s) for {selected} suitable for '{customer_area_type}' area.")
        for i, tip in enumerate(final_display_tips):
             headline = tip.get('headline', 'No Headline')
             with st.expander(f"💡 Tip {i+1}: {headline}", expanded=True): 
                st.write(f"{tip.get('description', 'No Description')}")
                rowid = tip.get('rowid', 'N/A')
                # Optionally show the simulated suitability for debugging:
                # suitability_debug = get_tip_suitability(tip)
                # details = f"Suitability: `{suitability_debug}` | RowID: `{rowid}` | Rule: `{tip.get('rule', 'N/A')}` | Category: `{tip.get('category', 'N/A')}` | Fuel: `{tip.get('fuel', 'N/A') or 'Any'}`"
                details = f"RowID: `{rowid}` | Rule: `{tip.get('rule', 'N/A')}` | Category: `{tip.get('category', 'N/A')}` | Fuel: `{tip.get('fuel', 'N/A') or 'Any'}`"
                st.caption(details)
    else:
        st.info(f"No specific tips found for '{selected}' suitable for a '{customer_area_type}' area that also match the current profile.")
        
    # Add a button to go back / select another category
    if st.button("⬅️ Back to Categories", key="back_btn"):
        st.session_state.selected_appliance = None
        st.rerun()

# --- Chat Input Area ---
# Display Chat Input ONLY if NO appliance is selected (avoid input while viewing tips)
if not st.session_state.selected_appliance:
     if prompt := st.chat_input("Enter Customer ID (e.g., CUST123)", disabled=st.session_state.processing, key="chat_input_main"):
         process_custid_input(prompt.strip()) 
