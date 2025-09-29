import streamlit as st
import pickle
import numpy as np
import os
import joblib
import pandas as pd
from streamlit_option_menu import option_menu
import re

import os
from google.cloud import translate_v2
from dotenv import load_dotenv
load_dotenv()

translate_client = translate_v2.Client()

LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "or": "Odia"
}

if "language" not in st.session_state:
    st.session_state.language = "en"

# Add caching for translations
if "translation_cache" not in st.session_state:
    st.session_state.translation_cache = {}

def _(text):
    lang = st.session_state.language
    if lang == "en":
        return text
    
    # Check cache first
    cache_key = f"{lang}_{text}"
    if cache_key in st.session_state.translation_cache:
        return st.session_state.translation_cache[cache_key]
    
    try:
        result = translate_client.translate(text, target_language=lang)
        translated = result["translatedText"]
        # Cache the result
        st.session_state.translation_cache[cache_key] = translated
        return translated
    except Exception:
        return text

# Move smart translation functions to global scope
def categorize_text(text):
    """Categorize text to determine best translation approach"""
    if re.match(r'^[A-Z][a-z]+ Pradesh$', text):
        return "state"
    elif text in ['Andaman and Nicobar Islands', 'Dadra and Nagar Haveli', 'Jammu and Kashmir']:
        return "territory"
    elif text.endswith('nuts') or text.endswith('gram') or 'pepper' in text.lower() or text in ['Horsegram']:
        return "compound_crop"
    elif text in ['Kharif', 'Rabi']:
        return "season_hindi"
    elif text in ['Gujarat', 'Karnataka', 'Punjab', 'Haryana', 'Kerala', 'Tamil Nadu', 'Telangana', 'Maharashtra', 'Rajasthan']:
        return "state"
    else:
        return "general"

def smart_translate_by_category(text):
    """Translate based on text category with caching"""
    lang = st.session_state.language
    if lang == "en":
        return text
    
    # Check cache first
    cache_key = f"smart_{lang}_{text}"
    if cache_key in st.session_state.translation_cache:
        return st.session_state.translation_cache[cache_key]
    
    category = categorize_text(text)
    
    try:
        if category == "state":
            result = translate_client.translate(f"the state of {text}", target_language=lang)
            translated = result["translatedText"]
            state_prefix_result = translate_client.translate("the state of", target_language=lang)
            state_prefix = state_prefix_result["translatedText"]
            translated = translated.replace(state_prefix, "").strip()
            
        elif category == "territory":
            if text == "Dadra and Nagar Haveli":
                territory_result = translate_client.translate("Dadra and Nagar Haveli union territory", target_language=lang)
                union_result = translate_client.translate("union territory", target_language=lang)
                translated = territory_result["translatedText"].replace(union_result["translatedText"], "").strip()
            else:
                result = translate_client.translate(text, target_language=lang)
                translated = result["translatedText"]
            
        elif category == "compound_crop":
            if text == "Soyabean":
                result = translate_client.translate("Soybean", target_language=lang)
                translated = result["translatedText"]
            elif text == "Blackpepper":
                black_result = translate_client.translate("Black", target_language=lang)
                pepper_result = translate_client.translate("Pepper", target_language=lang)
                translated = f"{black_result['translatedText']} {pepper_result['translatedText']}"
            elif text == "Cashewnuts":
                result = translate_client.translate("Cashew nuts", target_language=lang)
                translated = result["translatedText"]
            elif text == "Ladyfinger":
                result = translate_client.translate("Okra", target_language=lang)
                translated = result["translatedText"]
            elif text == "Sweetpotato":
                result = translate_client.translate("Sweet Potato", target_language=lang)
                translated = result["translatedText"]
            elif text == "Horsegram":
                result = translate_client.translate("Horse gram", target_language=lang)
                translated = result["translatedText"]
            else:
                result = translate_client.translate(text, target_language=lang)
                translated = result["translatedText"]
        
        elif category == "season_hindi":
            result = translate_client.translate(text, target_language=lang)
            translated = result["translatedText"]
        
        else:
            result = translate_client.translate(text, target_language=lang)
            translated = result["translatedText"]
        
        # Cache the result
        st.session_state.translation_cache[cache_key] = translated
        return translated
            
    except Exception as e:
        print(f"Translation error for '{text}': {e}")
        return text

def translate_list_smart(items):
    """Translate a list of items using smart translation"""
    return [smart_translate_by_category(item) for item in items]

# Add a simpler approach for dropdown translations
@st.cache_data
def get_translated_options(items, lang):
    """Cache translated dropdown options"""
    if lang == "en":
        return items
    
    translated = []
    for item in items:
        try:
            # Use simple translation for dropdown options
            result = translate_client.translate(item, target_language=lang)
            translated.append(result["translatedText"])
        except:
            translated.append(item)
    return translated

lang_display = st.sidebar.selectbox(
    "🌐 " + _("Select Language"),
    options=list(LANGUAGES.keys()),
    format_func=lambda x: LANGUAGES[x],
    index=list(LANGUAGES.keys()).index(st.session_state.language),
)
if st.session_state.language != lang_display:
    st.session_state.language = lang_display
    st.rerun()

def translate_markdown(md_text):
    lines = md_text.split('\n')
    translated_lines = []
    for line in lines:
        if line.strip():
            translated_lines.append(_(line))
        else:
            translated_lines.append('')
    return '\n'.join(translated_lines)

def translate_list(items):
    """Translate a list of items"""
    return [_(item) for item in items]

def get_original_value(translated_value, original_list, translated_list):
    """Get the original English value from translated value"""
    try:
        index = translated_list.index(translated_value)
        return original_list[index]
    except ValueError:
        return translated_value

st.set_page_config(
    page_title=_("Fasal Vikas"),
    page_icon=":corn:",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_yield_recommendations(crop, area, season, pH, rainfall, temperature, production, predicted_yield):
    recs = []

    # Area-based suggestions
    if area < 1:
        recs.append(
            _(f"Your cultivation area for {crop} is small ({area:.2f} hectares). Use high-yielding seed varieties, optimize plant spacing, and apply organic manure to maximize output.")
        )
    elif area > 10:
        recs.append(
            _(f"With a large area ({area:.2f} hectares) for {crop}, mechanize sowing and harvesting, and use precision agriculture tools for efficient resource management.")
        )

    # Crop-specific recommendations
    crop_lower = crop.lower()
    season_lower = season.lower()

    if crop_lower == "rice":
        if season_lower == "kharif" and rainfall < 60:
            recs.append(
                _("Rice in Kharif season needs at least 60 mm rainfall. Use alternate wetting and drying irrigation, and maintain proper bunds to conserve water.")
            )
        if pH < 6.0 or pH > 7.5:
            recs.append(
                _(f"Rice grows best in soil pH between 6.0 and 7.5. Your pH is {pH:.2f}. Apply lime if pH is low, or gypsum if pH is high.")
            )
        recs.append(
            _("Apply recommended doses of nitrogen, phosphorus, and potassium fertilizers at key growth stages. Use certified disease-free seeds.")
        )
        recs.append(
            _("Monitor for blast and bacterial leaf blight. Use resistant varieties and follow integrated pest management.")
        )
        recs.append(
            _("Harvest at the right moisture content (20-24%) to reduce post-harvest losses.")
        )

    elif crop_lower == "wheat":
        if season_lower == "rabi" and temperature < 15:
            recs.append(
                _(f"Wheat in Rabi season prefers temperatures above 15°C. Use early sowing and select cold-tolerant varieties.")
            )
        if pH < 6.0 or pH > 7.0:
            recs.append(
                _(f"Wheat prefers soil pH between 6.0 and 7.0. Your pH is {pH:.2f}. Apply lime or sulfur as needed.")
            )
        recs.append(
            _("Ensure timely irrigation at crown root initiation and grain filling stages. Avoid waterlogging.")
        )
        recs.append(
            _("Apply balanced fertilizers and micronutrients, especially zinc and iron, for better grain quality.")
        )
        recs.append(
            _("Control rust and aphids using recommended fungicides and insecticides.")
        )
        recs.append(
            _("Harvest when grains are hard and straw is dry for maximum yield.")
        )

    elif crop_lower == "cotton":
        if temperature < 20:
            recs.append(
                _(f"Cotton prefers warmer temperatures. Current temperature is {temperature:.1f}°C. Delay sowing or use protective covers if possible.")
            )
        if season_lower == "kharif":
            recs.append(
                _("Monitor for bollworm and whitefly. Use pheromone traps and biocontrol agents.")
            )
        recs.append(
            _("Apply nitrogen in split doses and ensure adequate potassium for boll development.")
        )
        recs.append(
            _("Practice timely irrigation, especially during flowering and boll formation.")
        )
        recs.append(
            _("Harvest cotton when bolls are fully mature and open to avoid quality loss.")
        )

    elif crop_lower == "soyabean":
        if rainfall < 40:
            recs.append(
                _(f"Soyabean needs at least 40 mm rainfall. Current rainfall is {rainfall:.1f} mm. Use supplemental irrigation if needed.")
            )
        if season_lower == "kharif":
            recs.append(
                _("Sow at the onset of monsoon for best results. Practice weed management during early growth.")
            )
        recs.append(
            _("Apply phosphorus and potassium fertilizers at sowing. Use rhizobium inoculation for better nitrogen fixation.")
        )
        recs.append(
            _("Monitor for yellow mosaic virus and use resistant varieties.")
        )
        recs.append(
            _("Harvest when pods turn yellow and seeds rattle inside for maximum yield.")
        )

    # Season-based suggestions
    if season_lower == "summer" and temperature > 35:
        recs.append(
            _(f"High temperatures in Summer can stress {crop}. Use mulching, shade nets, and timely irrigation to reduce heat stress.")
        )

    # Soil health and fertilizer management
    if pH < 5.5:
        recs.append(
            _("Very acidic soil detected. Apply lime and organic matter to improve pH and nutrient availability.")
        )
    elif pH > 8.0:
        recs.append(
            _("Alkaline soil detected. Apply gypsum and organic compost to lower pH and enhance crop growth.")
        )

    # Yield comparison and improvement
    if area > 0 and predicted_yield < (production / area):
        recs.append(
            _(f"Your predicted yield ({predicted_yield:.2f} tons/hectare) is below your current average. Review fertilizer schedule, irrigation timing, and pest management for {crop}.")
        )
        recs.append(
            _("Consider soil testing and consult local agricultural experts for customized advice.")
        )

    # General best practices for maximum yield
    recs.append(
        _(f"Regularly monitor your {crop} field for weeds and pests, especially during the {season} season. Timely intervention can prevent yield loss.")
    )
    recs.append(
        _("Follow crop rotation and intercropping to maintain soil fertility and reduce pest pressure.")
    )
    recs.append(
        _("Keep records of all farm activities and inputs to track what works best for your field.")
    )

    return recs

def get_detailed_crop_plan(crop, state, season, area, pH, rainfall, temperature):
    """Generate detailed crop management plan for specific crop-state-season combination"""
    
    # Check if this is our detailed plan case for West Bengal
    if (crop.lower() == "rice" and 
        state.lower() == "west bengal" and 
        season.lower() == "kharif"):
        
        plan = {
            "crop": "Rice",
            "state": "West Bengal", 
            "season": "Kharif",
            "duration": "120 days",
            "variety_recommended": "IET 4786 (Bishnu) or Swarna Sub-1",
            "detailed_plan": []
        }
        
        # Pre-planting phase (Days -15 to 0)
        plan["detailed_plan"].extend([
            {
                "phase": _("Pre-Planting Preparation"),
                "days": _("15 days before sowing"),
                "activities": [
                    _("Land preparation: Deep ploughing 2-3 times when soil moisture is 18-20%"),
                    _("Apply 2-3 tons of well-decomposed FYM or compost per hectare"),
                    _("Level the field properly for uniform water distribution"),
                    _("Prepare nursery beds (400 sq.m for 1 hectare)"),
                    _("Treat seeds with Carbendazim @ 2g/kg seeds")
                ],
                "irrigation": _("Pre-sowing irrigation: 8-10 cm water depth"),
                "fertilizer": _("Basal application: 60 kg N + 30 kg P2O5 + 30 kg K2O per hectare")
            }
        ])
        
        # Nursery phase (Days 1-25)
        plan["detailed_plan"].extend([
            {
                "phase": _("Nursery Phase"),
                "days": _("Days 1-25"),
                "activities": [
                    _("Sow pre-treated seeds @ 40-50 kg/hectare in nursery"),
                    _("Maintain 2-3 cm water level in nursery beds"),
                    _("Apply urea @ 10 kg/400 sq.m nursery on day 10"),
                    _("Monitor for blast disease and apply Tricyclazole if needed")
                ],
                "irrigation": _("Daily light irrigation - 2-3 cm water depth"),
                "fertilizer": _("Day 10: Urea 10 kg per 400 sq.m nursery area")
            }
        ])
        
        # Transplanting phase (Days 25-30)
        plan["detailed_plan"].extend([
            {
                "phase": _("Transplanting"),
                "days": _("Days 25-30"),
                "activities": [
                    _("Transplant 25-30 day old seedlings"),
                    _("Spacing: 20cm x 15cm (2-3 seedlings per hill)"),
                    _("Complete transplanting within 5 days"),
                    _("Apply 2,4-D @ 1kg/hectare on day 3 after transplanting for weed control")
                ],
                "irrigation": _("Maintain 3-5 cm standing water throughout transplanting"),
                "fertilizer": _("No fertilizer application during transplanting")
            }
        ])
        
        # Vegetative growth phase (Days 30-65)
        plan["detailed_plan"].extend([
            {
                "phase": _("Vegetative Growth"),
                "days": _("Days 30-65"),
                "activities": [
                    _("First weeding and top dressing on day 35"),
                    _("Second weeding on day 50"),
                    _("Monitor for stem borer and apply Cartap Hydrochloride if needed"),
                    _("Check for bacterial leaf blight symptoms")
                ],
                "irrigation": _("Days 30-35: 5-7 cm water depth\nDays 36-50: 3-5 cm water depth\nDays 51-65: 5-8 cm water depth"),
                "fertilizer": _("Day 35: Apply 30 kg N (65 kg Urea) per hectare\nDay 50: Apply remaining 30 kg N (65 kg Urea) per hectare")
            }
        ])
        
        # Reproductive phase (Days 65-95)
        plan["detailed_plan"].extend([
            {
                "phase": _("Reproductive Phase (Panicle Initiation to Flowering)"),
                "days": _("Days 65-95"),
                "activities": [
                    _("Critical water management - maintain continuous flooding"),
                    _("Apply potash if deficiency symptoms appear"),
                    _("Monitor for blast disease in panicles"),
                    _("Check for brown plant hopper and apply Imidacloprid if needed")
                ],
                "irrigation": _("Days 65-80: 8-10 cm continuous flooding\nDays 81-95: 5-8 cm water depth (most critical period)"),
                "fertilizer": _("Day 70: Apply 15 kg K2O (25 kg MOP) if soil test shows deficiency")
            }
        ])
        
        # Grain filling phase (Days 95-115)
        plan["detailed_plan"].extend([
            {
                "phase": _("Grain Filling"),
                "days": _("Days 95-115"),
                "activities": [
                    _("Continue monitoring water levels"),
                    _("Watch for rice bug and apply Malathion if needed"),
                    _("Prepare for harvest - arrange machinery/labor"),
                    _("Check grain moisture content weekly")
                ],
                "irrigation": _("Days 95-105: 3-5 cm water depth\nDays 106-115: Gradually reduce to 1-2 cm\nStop irrigation 7 days before harvest"),
                "fertilizer": _("No fertilizer application during grain filling")
            }
        ])
        
        # Harvest phase (Days 115-120)
        plan["detailed_plan"].extend([
            {
                "phase": _("Harvest"),
                "days": _("Days 115-120"),
                "activities": [
                    _("Harvest when 85% grains turn golden yellow"),
                    _("Moisture content should be 20-22% for safe storage"),
                    _("Use combine harvester or manual harvesting"),
                    _("Dry grains to 14% moisture content immediately after harvest")
                ],
                "irrigation": _("Field should be dry during harvest"),
                "fertilizer": _("No fertilizer application")
            }
        ])
        
        # Summary
        plan["summary"] = {
            "total_water_requirement": _("1200-1500 mm throughout the season"),
            "total_fertilizer": _("120 kg N + 30 kg P2O5 + 30-45 kg K2O per hectare"),
            "expected_yield": _("4.5-5.5 tons per hectare"),
            "critical_stages": [
                _("Transplanting (Days 25-30)"),
                _("Panicle initiation (Days 65-75)"),
                _("Flowering (Days 85-95)")
            ],
            "key_practices": [
                _("Maintain continuous flooding during reproductive phase"),
                _("Apply fertilizers in 3 splits for better efficiency"),
                _("Monitor pest and disease regularly"),
                _("Ensure proper drainage before harvest")
            ]
        }
        
        return plan
    
    # NEW: Check if this is Rice in Odisha during Kharif season
    elif (crop.lower() == "rice" and 
          state.lower() == "odisha" and 
          season.lower() == "kharif"):
        
        plan = {
            "crop": "Rice",
            "state": "Odisha", 
            "season": "Kharif",
            "duration": "130 days",
            "variety_recommended": "Lalat, Pooja, or Improved Lalat (cyclone resistant)",
            "detailed_plan": []
        }
        
        # Pre-monsoon preparation (Days -20 to 0)
        plan["detailed_plan"].extend([
            {
                "phase": _("Pre-Monsoon Preparation"),
                "days": _("20 days before monsoon (May 15 - June 5)"),
                "activities": [
                    _("Summer ploughing 2-3 times for pest control and soil health"),
                    _("Apply 3-4 tons of well-decomposed FYM or compost per hectare"),
                    _("Construct/repair field bunds for water conservation"),
                    _("Prepare community nursery beds on higher ground"),
                    _("Seed treatment with Pseudomonas @ 10g/kg for disease resistance"),
                    _("Check drainage channels for cyclone preparedness")
                ],
                "irrigation": _("Depends on pre-monsoon showers, light irrigation if needed"),
                "fertilizer": _("Basal application: 40 kg N + 40 kg P2O5 + 40 kg K2O per hectare (higher K for cyclone resistance)")
            }
        ])
        
        # Monsoon nursery phase (Days 1-30)
        plan["detailed_plan"].extend([
            {
                "phase": _("Monsoon Nursery Phase"),
                "days": _("Days 1-30 (June 5 - July 5)"),
                "activities": [
                    _("Sow seeds @ 60-80 kg/hectare in nursery (higher density for cyclone backup)"),
                    _("Maintain 2-5 cm water level depending on rainfall"),
                    _("Apply neem cake @ 250 kg/hectare for pest management"),
                    _("Monitor weather forecast for cyclone warnings"),
                    _("Apply urea @ 15 kg/400 sq.m nursery on day 15")
                ],
                "irrigation": _("Rainwater dependent - supplement only if rainfall <50mm/week"),
                "fertilizer": _("Day 15: Urea 15 kg per 400 sq.m nursery area\nDay 25: MOP 5 kg per 400 sq.m for strengthening")
            }
        ])
        
        # Transplanting phase (Days 30-40)
        plan["detailed_plan"].extend([
            {
                "phase": _("Transplanting (Peak Monsoon)"),
                "days": _("Days 30-40 (July 5 - July 15)"),
                "activities": [
                    _("Transplant 30-35 day old robust seedlings"),
                    _("Wider spacing: 25cm x 20cm for better wind resistance"),
                    _("Plant 3-4 seedlings per hill for cyclone tolerance"),
                    _("Complete transplanting before peak monsoon intensity"),
                    _("Apply Butachlor @ 1.25 kg/hectare for weed control on day 3")
                ],
                "irrigation": _("Maintain 5-8 cm standing water, monitor for excess water drainage"),
                "fertilizer": _("No fertilizer during transplanting - focus on establishment")
            }
        ])
        
        # Vegetative growth phase (Days 40-80)
        plan["detailed_plan"].extend([
            {
                "phase": _("Vegetative Growth (Monsoon Peak)"),
                "days": _("Days 40-80 (July 15 - August 25)"),
                "activities": [
                    _("First top dressing and weeding on day 45"),
                    _("Second weeding and earthing up on day 60 for wind resistance"),
                    _("Monitor for blast and sheath blight (high humidity diseases)"),
                    _("Apply Triazophos for stem borer control if needed"),
                    _("Check field drainage after heavy rainfall events"),
                    _("Foliar spray of potash @ 1% for strength on day 70")
                ],
                "irrigation": _("Days 40-60: 8-12 cm water depth (monsoon peak)\nDays 61-80: 5-8 cm water depth\nEnsure proper drainage during heavy rains"),
                "fertilizer": _("Day 45: Apply 40 kg N (87 kg Urea) per hectare\nDay 65: Apply remaining 40 kg N (87 kg Urea) per hectare\nDay 70: Foliar KCl spray 1%")
            }
        ])
        
        # Reproductive phase (Days 80-110)
        plan["detailed_plan"].extend([
            {
                "phase": _("Reproductive Phase (Late Monsoon - Post Monsoon)"),
                "days": _("Days 80-110 (August 25 - September 25)"),
                "activities": [
                    _("Critical period - monitor weather for cyclones"),
                    _("Maintain continuous flooding for panicle development"),
                    _("Apply additional potash if cyclone warning issued"),
                    _("Monitor for neck blast and false smut"),
                    _("Install bird scarers as grains start filling"),
                    _("Prepare drainage for post-monsoon excess water")
                ],
                "irrigation": _("Days 80-95: 10-15 cm continuous flooding (critical stage)\nDays 96-110: 8-10 cm water depth\nPrepare for cyclone drainage if needed"),
                "fertilizer": _("Day 85: Apply 20 kg K2O (33 kg MOP) per hectare for grain filling\nEmergency K spray if cyclone expected")
            }
        ])
        
        # Grain filling phase (Days 110-125)
        plan["detailed_plan"].extend([
            {
                "phase": _("Grain Filling (Post-Monsoon)"),
                "days": _("Days 110-125 (September 25 - October 10)"),
                "activities": [
                    _("Reduce water levels gradually"),
                    _("Monitor for rice bugs and apply Malathion if needed"),
                    _("Watch for cyclone warnings and harvest early if needed"),
                    _("Check grain moisture content twice weekly"),
                    _("Prepare harvesting equipment and labor"),
                    _("Apply Propiconazole for grain diseases if humidity is high")
                ],
                "irrigation": _("Days 110-120: 3-5 cm water depth\nDays 121-125: 1-2 cm water depth\nStop irrigation 5-7 days before harvest"),
                "fertilizer": _("No fertilizer application - focus on crop protection")
            }
        ])
        
        # Harvest phase (Days 125-130)
        plan["detailed_plan"].extend([
            {
                "phase": _("Harvest (Pre-Winter)"),
                "days": _("Days 125-130 (October 10 - October 15)"),
                "activities": [
                    _("Harvest when 80-85% grains are golden (earlier than usual for cyclone safety)"),
                    _("Target moisture content: 18-20% for Odisha conditions"),
                    _("Use combine harvester if fields are accessible"),
                    _("Immediate drying to 14% moisture using solar dryers"),
                    _("Store in moisture-proof containers for cyclone season"),
                    _("Keep some paddy unhusked for better storage")
                ],
                "irrigation": _("Field should be dry but not cracked - maintain some moisture for machinery"),
                "fertilizer": _("No fertilizer application")
            }
        ])
        
        # Summary for Odisha conditions
        plan["summary"] = {
            "total_water_requirement": _("1500-1800 mm (monsoon dependent, cyclone considerations)"),
            "total_fertilizer": _("120 kg N + 40 kg P2O5 + 60 kg K2O per hectare (higher K for cyclone resistance)"),
            "expected_yield": _("3.5-4.5 tons per hectare (cyclone-resistant varieties)"),
            "critical_stages": [
                _("Nursery protection (June monsoon)"),
                _("Transplanting timing (before peak monsoon)"),
                _("Panicle initiation (cyclone season - Aug-Sep)"),
                _("Early harvest (before October cyclones)")
            ],
            "key_practices": [
                _("Cyclone-resistant variety selection essential"),
                _("Higher potassium application for wind resistance"),
                _("Wider spacing and stronger seedlings"),
                _("Weather monitoring and early harvest planning"),
                _("Proper drainage system for excess water management"),
                _("Community nursery approach for risk reduction")
            ],
            "odisha_specific": [
                _("🌀 Cyclone preparedness: Monitor IMD warnings regularly"),
                _("🌊 Drainage: Essential for managing monsoon excess water"),
                _("🌾 Varieties: Use Lalat/Pooja for local adaptation"),
                _("🏪 Storage: Cyclone-safe storage facilities needed"),
                _("👥 Community approach: Share resources for risk management")
            ]
        }
        
        return plan
    
    else:
        # Return general recommendations for other combinations
        return None

def display_detailed_crop_plan(crop, state, season, area, pH, rainfall, temperature):
    """Display detailed crop management plan"""
    plan = get_detailed_crop_plan(crop, state, season, area, pH, rainfall, temperature)
    
    if plan:
        st.success(_("🌾 Detailed Crop Management Plan Available!"))
        
        # Display header info
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(_("Crop"), _(plan["crop"]))
        with col2:
            st.metric(_("State"), _(plan["state"]))
        with col3:
            st.metric(_("Season"), _(plan["season"]))
        with col4:
            st.metric(_("Duration"), _(plan["duration"]))
        
        st.info(_(f"**Recommended Variety:** {plan['variety_recommended']}"))
        
        # Special Odisha-specific alerts
        if plan["state"].lower() == "odisha":
            st.warning(_("⚠️ **Cyclone Zone Alert**: This plan includes cyclone preparedness measures specific to Odisha's coastal conditions."))
            
            with st.expander(_("🌀 Odisha-Specific Considerations"), expanded=True):
                for consideration in plan["summary"]["odisha_specific"]:
                    st.markdown(f"• {consideration}")
        
        # Display detailed timeline
        st.markdown(_("## 📅 Detailed Timeline and Activities"))
        
        for phase in plan["detailed_plan"]:
            with st.expander(f"📋 {phase['phase']} - {phase['days']}", expanded=False):
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(_("**Activities:**"))
                    for activity in phase["activities"]:
                        st.markdown(f"• {activity}")
                
                with col2:
                    st.markdown(_("**💧 Irrigation:**"))
                    st.info(phase["irrigation"])
                    
                    st.markdown(_("**🌱 Fertilizer:**"))
                    st.success(phase["fertilizer"])
        
        # Display summary
        st.markdown(_("## 📊 Summary & Key Information"))
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(_("**💧 Total Water Requirement:**"))
            st.info(plan["summary"]["total_water_requirement"])
            
            st.markdown(_("**🌱 Total Fertilizer Requirement:**"))
            st.success(plan["summary"]["total_fertilizer"])

            st.markdown(_("**✅ Key Practices:**"))
            for practice in plan["summary"]["key_practices"]:
                st.markdown(f"• {practice}")
        
        
        with col2:
            st.markdown(_("**⚠️ Critical Stages:**"))
            for stage in plan["summary"]["critical_stages"]:
                st.warning(stage)
            

        return True
    
    return False

# Loading all the models
working_dir = os.path.dirname(os.path.abspath(__file__))
crop_recom_model = pickle.load(open(f'{working_dir}/RF_Crop.sav', 'rb'))
crop_yield_model = joblib.load(open(f'{working_dir}/voting_yield.sav', 'rb'))

# Set background color
st.markdown(
    """
    <style>
        body {
            background-color: #f0f5f5;
        }
        .profile-pic {
            border-radius: 50%;
            width: 150px;
            height: 150px;
            object-fit: cover;
            margin-bottom: 10px;
        }
        .profile-column {
            text-align: center;
            padding: 20px;
        }
        .icon {
            width: 24px;
            height: 24px;
            margin: 0 5px;
        }
        .profile-name {
            font-size: 18px;
            font-weight: bold;
            margin-top: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    # Store original options in English
    original_options = ["Home", "Crop Yield Prediction", "Crop Recommendation", "Meet the Creators"]
    
    # Translate options for display
    translated_options = [_(option) for option in original_options]
    
    selected_translated = option_menu(_("Fasal Vikas"),
                           translated_options,
                           menu_icon=":seedling:",
                           icons=["house", "tree", "tree", "people"],
                           default_index=0)
    
    # Get the original English option for comparison
    try:
        selected_index = translated_options.index(selected_translated)
        selected = original_options[selected_index]
    except ValueError:
        selected = "Home"  # fallback

# Crop Recommendation
if selected == "Crop Recommendation":
    st.title(_("Crop Recommendation"))

    st.write(_("Provide the following information to get crop recommendations:"))
    st.write(_("""
    - **Nitrogen (N)**: Essential nutrient for plant growth.
    - **Phosphorus (P)**: Vital for root development and energy transfer.
    - **Potassium (K)**: Important for water regulation and disease resistance.
    - **pH Value**: Soil acidity or alkalinity level.
    - **Temperature (°C)**: Current temperature.
    - **Humidity (%)**: Moisture content in the air.
    - **Rainfall (mm)**: Amount of recent rainfall.
    """))

    N = st.number_input(_("Nitrogen (N)"), min_value=0, value=0)
    P = st.number_input(_("Phosphorus (P)"), min_value=0, value=0)
    K = st.number_input(_("Potassium (K)"), min_value=0, value=0)
    pH = st.number_input(_("pH Value"), min_value=0.0, max_value=14.0, value=0.0)
    temperature = st.number_input(_("Temperature (°C)"), min_value=0.0, value=0.0)
    humidity = st.number_input(_("Humidity (%)"), min_value=0.0, max_value=100.0, value=0.0)
    rainfall = st.number_input(_("Rainfall (mm)"), min_value=0.0, value=0.0)
    
    if st.button(_("Recommend Crop")):
        crop_input = np.array([[N, P, K, pH, temperature, humidity, rainfall]])
        
        if all(crop_input[0][:3]):  # Check if N, P, K values are provided
            crop_recommendation = crop_recom_model.predict(crop_input)
            st.success(_(f"Recommended Crop: {crop_recommendation[0]}"))
        else:
            st.error(_("Please enter values for Nitrogen (N), Phosphorus (P), and Potassium (K)"))

# Crop Yield Prediction
elif selected == "Crop Yield Prediction":
    st.title(_("Crop Yield Prediction"))
    st.write("")
    st.markdown(translate_markdown("""
### Using the Crop Yield Prediction Model

- **Select State**: Choose the state where the crop is being cultivated.
- **Select Crop**: Pick the specific crop for yield prediction.
- **Select Season**: Choose the appropriate growing season.
- **Input Soil pH**: Enter the soil pH level. [Measure pH at home](https://www.youtube.com/watch?v=mZgxUqoJMcg).
- **Input Rainfall**: Enter the rainfall amount (mm). [Check local rainfall](https://mausam.imd.gov.in/responsive/rainfallinformation.php).
- **Input Temperature**: Enter the average temperature (°C). [Check local temperature](https://www.accuweather.com/).
- **Input Area**: Enter the cultivation area (hectares).
- **Input Production**: Enter the total production (tons).
- **Click Predict**: Get the yield prediction.
### Interpreting Results

- Predicted yield is shown in tons per hectare.
- Use this data for crop management and planning.

Leverage machine learning for accurate crop yield predictions to enhance productivity and sustainability.
"""))

    states = ['Andaman and Nicobar Islands', 'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chandigarh', 'Chhattisgarh', 
              'Dadra and Nagar Haveli', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 
              'Jammu and Kashmir', 'Jharkhand', 'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 
              'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Puducherry', 'Punjab', 
              'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 
              'Uttarakhand', 'West Bengal']

    crops = ['Arecanut', 'Barley', 'Banana', 'Blackpepper', 'Brinjal', 'Cabbage', 'Cardamom', 'Cashewnuts', 'Cauliflower', 
             'Coriander', 'Cotton', 'Garlic', 'Grapes', 'Horsegram', 'Jowar', 'Jute', 'Ladyfinger', 'Maize', 
             'Mango', 'Moong', 'Onion', 'Orange', 'Papaya', 'Pineapple', 'Potato', 'Rapeseed', 'Ragi', 'Rice', 
             'Sesamum', 'Soyabean', 'Sunflower', 'Sweetpotato', 'Tapioca', 'Tomato', 'Turmeric', 'Wheat']

    seasons = ['Kharif', 'Rabi', 'Summer', 'Whole Year']

    # Use cached translation for better performance
    current_lang = st.session_state.language
    translated_states = get_translated_options(states, current_lang)
    translated_crops = get_translated_options(crops, current_lang)
    translated_seasons = get_translated_options(seasons, current_lang)

    # Display translated options but get original values
    state_translated = st.selectbox(_("Select State"), translated_states)
    crop_translated = st.selectbox(_("Select Crop"), translated_crops)
    season_translated = st.selectbox(_("Select Season"), translated_seasons)
        
    # Get original English values for processing
    state = get_original_value(state_translated, states, translated_states)
    crop = get_original_value(crop_translated, crops, translated_crops)
    season = get_original_value(season_translated, seasons, translated_seasons)

    pH = st.number_input(_("Soil pH Value"), min_value=0.0, max_value=14.0, value=0.0)
    rainfall = st.number_input(_("Rainfall (mm)"), min_value=0.0, value=0.0)
    temperature = st.number_input(_("Temperature (°C)"), min_value=0.0, value=0.0)
    area = st.number_input(_("Area (hectares)"), min_value=0.0, value=0.0)
    production = st.number_input(_("Production (tons)"), min_value=0.0, value=0.0)

    # Single button that handles both prediction and detailed plan
    if st.button(_("Predict Yield"), type="primary"):
        if state and crop and season and pH and rainfall and temperature and area and production:
            state_lower = state.lower()
            crop_lower = crop.lower()
            season_lower = season.lower()

            state_encoded = [0] * (len(states) - 1) if state_lower == 'andaman and nicobar islands' else [1 if s.lower() == state_lower else 0 for s in states if s.lower() != 'andaman and nicobar islands']
            crop_encoded = [0] * (len(crops) - 1) if crop_lower == 'arecanut' else [1 if c.lower() == crop_lower else 0 for c in crops if c.lower() != 'arecanut']
            season_encoded = [0] * (len(seasons) - 1) if season_lower == 'kharif' else [1 if s.lower() == season_lower else 0 for s in seasons if s.lower() != 'kharif']

            input_features = np.array(state_encoded + crop_encoded + season_encoded + [pH, rainfall, temperature, area, production]).reshape(1, -1)

            expected_num_features = len(states) + len(crops) + len(seasons) - 3 + 5

            if input_features.shape[1] != expected_num_features:
                st.error(_(f"Feature shape mismatch, expected: {expected_num_features}, got: {input_features.shape[1]}"))
            else:
                predicted_yield = crop_yield_model.predict(input_features)
                st.success(_(f'The predicted yield for the selected inputs is: {predicted_yield[0]:.2f} tons/hectare'))
                
                # Show tailored recommendations to improve yield
                recs = get_yield_recommendations(crop, area, season, pH, rainfall, temperature, production, predicted_yield[0])
                st.markdown(_("#### Recommendations to Improve Yield"))
                for r in recs:
                    st.info(r)
                
                # INTEGRATED: Check if detailed plan is available and display it
                detailed_plan = get_detailed_crop_plan(crop, state, season, area, pH, rainfall, temperature)
                if detailed_plan:
                    st.markdown("---")
                    st.markdown(_("# 🌾 **BONUS: Comprehensive Crop Management Plan**"))
                    st.markdown(_("Since you selected a special combination, here's your detailed farming plan:"))
                    display_detailed_crop_plan(crop, state, season, area, pH, rainfall, temperature)
        else:
            st.error(_("Please enter all required values"))

# Meet Creators
elif selected == "Meet the Creators":
    st.title(_("Meet the Creators"))
    st.markdown("<br>", unsafe_allow_html=True)

    creators = [
        {
            "name": "Aaron Thomas",
            "linkedin": "https://www.linkedin.com/in/aaron-jthomas/",
            "github": "https://github.com/AayJayTee",
            "image": "images/aaron.jpg"
        },
        {
            "name": "Saumyaa Garg",
            "linkedin": "https://www.linkedin.com/in/saumyaa-garg/",
            "github": "https://github.com/saumyaagarg",
            "image": "images/saumyaa.jpg"
        },
        {
            "name": "Yati",
            "linkedin": "https://www.linkedin.com/in/yati21/",
            "github": "https://github.com/Yati-21",
            "image": "images/yati.jpg"
        },
        {
            "name": "Ananya Gupta",
            "linkedin": "https://www.linkedin.com/in/ananya-gupta-513753258/",
            "github": "https://github.com/Ananyagupta1812",
            "image": "images/ananya.jpg"
        },
        {
            "name": "Chirag Dhooria",
            "linkedin": "https://www.linkedin.com/in/chirag-dhooria-324859305/",
            "github": "https://github.com/Chirag-Dhooria",
            "image": "images/randompfp.jpeg"
        },
        {
            "name": "Aanya Chauhan",
            "linkedin": "https://www.linkedin.com/in/aanyachauhan9/",
            "github": "https://github.com/aanyachauhan9",
            "image": "images/aanya.jpg"
        }
    ]

    # Display creators in two rows of three columns each
    for row_start in range(0, len(creators), 3):
        cols = st.columns(3)
        for i, creator in enumerate(creators[row_start:row_start+3]):
            with cols[i]:
                st.image(creator["image"], width=80, caption=None, use_container_width=True, output_format='auto')
                st.markdown(
                    f"<div class='profile-column'><p class='profile-name'>{(creator['name'])}</p>"
                    f"<a href='{creator['linkedin']}'><img src='https://upload.wikimedia.org/wikipedia/commons/8/81/LinkedIn_icon.svg' class='icon'></a> "
                    f"<a href='{creator['github']}'><img src='https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png' class='icon'></a></div>",
                    unsafe_allow_html=True
                )

# Home
else:
    img = "hero2.jpg"
    st.title(_("Fasal Vikas"))
    st.write(_("##### Welcome to Fasal Vikas! Explore our tools in the sidebar to make informed agricultural decisions."))
    st.image(img, width=750)
    
    st.write("")
    st.write(_("### Overview"))
    st.write(_("Fasal Vikas is an AI-powered platform designed to empower farmers with personalized crop recommendations and accurate yield predictions. By leveraging advanced machine learning models and real-time data, it helps optimize irrigation, fertilization, and pest management. The intuitive interface and actionable insights enable farmers to boost productivity, make informed decisions, and sustainably manage their agricultural practices."))
    st.write(_("### Find the Code at:"))
    st.write(_("Link: "))
    st.write(_("Made with 💖 by Saumyaa, Aaron, Yati, Ananya, Chirag, and Aanya"))