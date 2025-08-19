#!/usr/bin/env python3
"""
StoryForge AI - Phase 5: User Acceptance Testing (UAT)
User-perspective testing to validate system meets actual user requirements
"""

import json
import os
import sys
import time
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chronicler_agent import ChroniclerAgent
from director_agent import DirectorAgent, PersonaAgent
from character_factory import CharacterFactory
from config_loader import ConfigLoader

class UserAcceptanceTest:
    """Individual user acceptance test scenario"""
    
    def __init__(self, name: str, description: str, user_story: str, acceptance_criteria: List[str]):
        self.name = name
        self.description = description
        self.user_story = user_story
        self.acceptance_criteria = acceptance_criteria
        self.result = None
        self.passed = None
        self.execution_time = None
        self.user_feedback = {}
        self.evidence = []
        
    def execute(self, uat_framework) -> bool:
        """Execute the UAT scenario"""
        start_time = time.time()
        try:
            # This will be implemented by specific test methods
            self.result = self._run_scenario(uat_framework)
            self.passed = self._evaluate_acceptance_criteria()
        except Exception as e:
            self.result = {"error": str(e)}
            self.passed = False
        
        self.execution_time = time.time() - start_time
        return self.passed
        
    def _run_scenario(self, uat_framework):
        """Override in specific test implementations"""
        raise NotImplementedError
        
    def _evaluate_acceptance_criteria(self) -> bool:
        """Evaluate if acceptance criteria are met"""
        # Override in specific test implementations
        return self.result is not None and not isinstance(self.result, dict) or "error" not in self.result
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert UAT to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "user_story": self.user_story,
            "acceptance_criteria": self.acceptance_criteria,
            "passed": self.passed,
            "execution_time": self.execution_time,
            "user_feedback": self.user_feedback,
            "evidence": self.evidence,
            "result": self.result
        }

class StoryGenerationUAT(UserAcceptanceTest):
    """UAT for story generation functionality"""
    
    def __init__(self):
        super().__init__(
            name="story_generation_workflow",
            description="End-to-end story generation from user perspective",
            user_story="As a user, I want to generate engaging stories using different characters so that I can create compelling narratives for my campaign",
            acceptance_criteria=[
                "I can select characters from available options",
                "The system generates coherent stories with selected characters",
                "Character names are properly integrated in the generated content",
                "No 'For Unknown' or placeholder text appears in the output",
                "The story is engaging and makes narrative sense",
                "The generation completes within reasonable time (< 30 seconds)"
            ]
        )
    
    def _run_scenario(self, uat_framework):
        """Run story generation scenario as a user would"""
        results = {
            "steps_completed": [],
            "user_experience": {},
            "generated_content": {},
            "issues_encountered": []
        }
        
        try:
            # Step 1: User checks available characters
            print("   👤 USER: Let me see what characters are available...")
            factory = CharacterFactory()
            available_characters = factory.list_available_characters()
            
            results["steps_completed"].append("viewed_available_characters")
            results["user_experience"]["character_selection"] = {
                "characters_available": len(available_characters),
                "character_list": available_characters,
                "user_satisfaction": "satisfied" if len(available_characters) >= 2 else "unsatisfied"
            }
            
            if len(available_characters) < 2:
                results["issues_encountered"].append("Not enough characters available for story generation")
                return results
                
            # Step 2: User selects characters for story
            print(f"   👤 USER: I'll choose {available_characters[0]} and {available_characters[1]} for my story")
            selected_chars = available_characters[:2]
            results["user_experience"]["character_selection"]["selected_characters"] = selected_chars
            
            # Step 3: User initiates story generation
            print("   👤 USER: Starting story generation...")
            director = DirectorAgent()
            
            # Register the selected characters as agents
            agent1 = factory.create_character(selected_chars[0])
            agent2 = factory.create_character(selected_chars[1])
            
            director.register_agent(agent1)
            director.register_agent(agent2)
            
            results["steps_completed"].append("initialized_story_system")
            
            # Step 4: User executes a story turn
            print("   👤 USER: Generating story content...")
            story_result = director.run_turn()
            
            results["steps_completed"].append("generated_story_content")
            results["generated_content"]["story_result"] = story_result
            
            # Step 5: User reviews the generated content
            if story_result and "content" in story_result:
                content = story_result["content"]
                print("   👤 USER: Let me review the generated story...")
                
                # User evaluation criteria
                user_evaluation = {
                    "content_length": len(content),
                    "has_character_names": any(char in content for char in selected_chars),
                    "no_unknown_segments": "for unknown" not in content.lower(),
                    "has_narrative_structure": "." in content and len(content.split(".")) > 1,
                    "engaging_content": len(content) > 100 and not any(placeholder in content.lower() for placeholder in ["placeholder", "todo", "fixme"]),
                    "user_satisfaction": "very_satisfied"  # Will be updated based on actual evaluation
                }
                
                # Update user satisfaction based on evaluation
                issues_found = []
                if not user_evaluation["has_character_names"]:
                    issues_found.append("Character names not mentioned in story")
                if not user_evaluation["no_unknown_segments"]:
                    issues_found.append("Story contains 'For Unknown' segments")
                if not user_evaluation["has_narrative_structure"]:
                    issues_found.append("Story lacks proper narrative structure")
                if not user_evaluation["engaging_content"]:
                    issues_found.append("Story content is not engaging or contains placeholders")
                
                if len(issues_found) == 0:
                    user_evaluation["user_satisfaction"] = "very_satisfied"
                    self.user_feedback["overall"] = "The story generation worked perfectly! I'm impressed with the quality."
                elif len(issues_found) <= 2:
                    user_evaluation["user_satisfaction"] = "satisfied_with_minor_issues"
                    self.user_feedback["overall"] = f"Good story generation with some minor issues: {', '.join(issues_found)}"
                else:
                    user_evaluation["user_satisfaction"] = "unsatisfied"
                    self.user_feedback["overall"] = f"Story generation has significant issues: {', '.join(issues_found)}"
                
                results["user_experience"]["content_evaluation"] = user_evaluation
                results["issues_encountered"].extend(issues_found)
                results["steps_completed"].append("reviewed_generated_content")
                
                # Store evidence for later review
                self.evidence.append({
                    "type": "generated_story",
                    "content": content[:500],  # First 500 chars for evidence
                    "selected_characters": selected_chars,
                    "user_evaluation": user_evaluation
                })
                
            else:
                results["issues_encountered"].append("No story content was generated")
                self.user_feedback["overall"] = "The system failed to generate any story content. This is unacceptable."
                
        except Exception as e:
            results["issues_encountered"].append(f"System error during story generation: {str(e)}")
            self.user_feedback["overall"] = f"The system crashed during use. Error: {str(e)}"
        
        return results
    
    def _evaluate_acceptance_criteria(self) -> bool:
        """Evaluate acceptance criteria from user perspective"""
        if not self.result or "error" in self.result:
            return False
        
        result = self.result
        
        # Check each acceptance criterion
        criteria_met = 0
        total_criteria = len(self.acceptance_criteria)
        
        # Characters available and selectable
        if "viewed_available_characters" in result.get("steps_completed", []):
            criteria_met += 1
        
        # Story generation completed
        if "generated_story_content" in result.get("steps_completed", []) and result.get("generated_content"):
            criteria_met += 1
        
        # Character integration check
        user_exp = result.get("user_experience", {}).get("content_evaluation", {})
        if user_exp.get("has_character_names", False):
            criteria_met += 1
        
        # No unknown segments
        if user_exp.get("no_unknown_segments", False):
            criteria_met += 1
        
        # Engaging content
        if user_exp.get("engaging_content", False):
            criteria_met += 1
        
        # Performance check (execution time)
        if self.execution_time and self.execution_time < 30:
            criteria_met += 1
        
        return criteria_met >= (total_criteria * 0.8)  # At least 80% of criteria met

class CampaignManagementUAT(UserAcceptanceTest):
    """UAT for campaign management functionality"""
    
    def __init__(self):
        super().__init__(
            name="campaign_management_workflow",
            description="Campaign log transcription from user perspective",
            user_story="As a user, I want to convert my campaign logs into narrative format so that I can share engaging stories of my gaming sessions",
            acceptance_criteria=[
                "I can provide a campaign log file to the system",
                "The system processes the campaign log without errors",
                "The output is a well-formatted narrative",
                "Character actions are properly transcribed",
                "The narrative maintains the essence of the original campaign",
                "The process completes in reasonable time"
            ]
        )
    
    def _run_scenario(self, uat_framework):
        """Run campaign management scenario as a user would"""
        results = {
            "steps_completed": [],
            "user_experience": {},
            "generated_narrative": {},
            "issues_encountered": []
        }
        
        try:
            # Step 1: User creates a campaign log (simulating real user content)
            print("   👤 USER: I have a campaign log from my recent gaming session that I want to convert to narrative...")
            
            campaign_log_content = """# Epic Space Campaign - Session 47
## Turn 1
- **pilot**: Carefully maneuvered the ship through the asteroid field, avoiding the larger chunks of debris
- **engineer**: Worked frantically to repair the damaged hull breach in section C-7
- **scientist**: Analyzed the strange energy readings coming from the derelict ship ahead

## Turn 2
- **pilot**: Engaged the docking sequence with the mysterious vessel
- **engineer**: Prepared emergency repair kits and structural support beams
- **scientist**: Detected unusual quantum signatures that don't match known technology

## Turn 3
- **pilot**: Successfully docked despite the ship's erratic spin
- **engineer**: Sealed the airlock and confirmed atmospheric pressure stability
- **scientist**: Recorded detailed scans of the alien technology for later analysis
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp_file:
                tmp_file.write(campaign_log_content)
                campaign_log_path = tmp_file.name
                
            results["steps_completed"].append("created_campaign_log")
            results["user_experience"]["log_creation"] = {
                "log_size": len(campaign_log_content),
                "characters_involved": ["pilot", "engineer", "scientist"],
                "turns_recorded": 3,
                "user_satisfaction": "satisfied"
            }
            
            # Step 2: User initiates transcription
            print("   👤 USER: Converting my campaign log to narrative format...")
            chronicler = ChroniclerAgent()
            
            results["steps_completed"].append("initialized_transcription_system")
            
            # Step 3: User processes the campaign log
            narrative_result = chronicler.transcribe_log(campaign_log_path)
            
            results["steps_completed"].append("processed_campaign_log")
            results["generated_narrative"]["narrative_content"] = narrative_result
            
            # Step 4: User reviews the narrative
            if narrative_result and len(narrative_result.strip()) > 0:
                print("   👤 USER: Let me review the generated narrative...")
                
                # User evaluation of the narrative
                user_evaluation = {
                    "narrative_length": len(narrative_result),
                    "has_proper_formatting": any(marker in narrative_result for marker in ["#", "**", "Generated:", "Source:"]),
                    "characters_mentioned": sum(1 for char in ["pilot", "engineer", "scientist"] if char in narrative_result.lower()),
                    "maintains_story_essence": "asteroid field" in narrative_result.lower() or "docking" in narrative_result.lower() or "quantum" in narrative_result.lower(),
                    "no_technical_artifacts": "for unknown" not in narrative_result.lower(),
                    "readable_format": len(narrative_result.split(".")) > 3,  # Has multiple sentences
                    "user_satisfaction": "satisfied"
                }
                
                # Evaluate user satisfaction
                issues_found = []
                if not user_evaluation["has_proper_formatting"]:
                    issues_found.append("Narrative lacks proper formatting")
                if user_evaluation["characters_mentioned"] < 2:
                    issues_found.append("Not all characters properly mentioned in narrative")
                if not user_evaluation["maintains_story_essence"]:
                    issues_found.append("Narrative doesn't capture the essence of the original campaign")
                if not user_evaluation["no_technical_artifacts"]:
                    issues_found.append("Narrative contains technical artifacts")
                if not user_evaluation["readable_format"]:
                    issues_found.append("Narrative is not well-formatted for reading")
                
                if len(issues_found) == 0:
                    user_evaluation["user_satisfaction"] = "very_satisfied"
                    self.user_feedback["overall"] = "Perfect! The narrative captures my campaign perfectly and reads like a real story."
                elif len(issues_found) <= 2:
                    user_evaluation["user_satisfaction"] = "satisfied_with_minor_issues"
                    self.user_feedback["overall"] = f"Good narrative with minor issues: {', '.join(issues_found)}"
                else:
                    user_evaluation["user_satisfaction"] = "unsatisfied"
                    self.user_feedback["overall"] = f"The narrative has significant problems: {', '.join(issues_found)}"
                
                results["user_experience"]["narrative_evaluation"] = user_evaluation
                results["issues_encountered"].extend(issues_found)
                results["steps_completed"].append("reviewed_generated_narrative")
                
                # Store evidence
                self.evidence.append({
                    "type": "campaign_narrative",
                    "original_log_excerpt": campaign_log_content[:300],
                    "generated_narrative_excerpt": narrative_result[:500],
                    "user_evaluation": user_evaluation
                })
                
            else:
                results["issues_encountered"].append("No narrative was generated from the campaign log")
                self.user_feedback["overall"] = "The system failed to generate any narrative from my campaign log."
            
            # Cleanup
            try:
                os.unlink(campaign_log_path)
            except:
                pass
                
        except Exception as e:
            results["issues_encountered"].append(f"System error during campaign transcription: {str(e)}")
            self.user_feedback["overall"] = f"The system encountered an error: {str(e)}"
        
        return results
    
    def _evaluate_acceptance_criteria(self) -> bool:
        """Evaluate acceptance criteria from user perspective"""
        if not self.result or "error" in self.result:
            return False
        
        result = self.result
        
        # Check each acceptance criterion
        criteria_met = 0
        total_criteria = len(self.acceptance_criteria)
        
        # Campaign log provided
        if "created_campaign_log" in result.get("steps_completed", []):
            criteria_met += 1
        
        # Processing completed
        if "processed_campaign_log" in result.get("steps_completed", []):
            criteria_met += 1
        
        # Well-formatted output
        user_exp = result.get("user_experience", {}).get("narrative_evaluation", {})
        if user_exp.get("has_proper_formatting", False):
            criteria_met += 1
        
        # Character actions transcribed
        if user_exp.get("characters_mentioned", 0) >= 2:
            criteria_met += 1
        
        # Story essence maintained
        if user_exp.get("maintains_story_essence", False):
            criteria_met += 1
        
        # Performance check
        if self.execution_time and self.execution_time < 60:
            criteria_met += 1
        
        return criteria_met >= (total_criteria * 0.8)

class SystemUsabilityUAT(UserAcceptanceTest):
    """UAT for overall system usability"""
    
    def __init__(self):
        super().__init__(
            name="system_usability_workflow",
            description="Overall system usability from user perspective",
            user_story="As a user, I want the system to be intuitive and reliable so that I can focus on creating content rather than fighting with the tool",
            acceptance_criteria=[
                "The system provides clear feedback when operations succeed or fail",
                "Error messages are user-friendly and actionable",
                "The system recovers gracefully from errors",
                "Operations complete within expected timeframes",
                "The system maintains consistency across multiple uses",
                "I can easily understand what the system is doing"
            ]
        )
    
    def _run_scenario(self, uat_framework):
        """Run usability scenario as a user would"""
        results = {
            "steps_completed": [],
            "user_experience": {},
            "usability_metrics": {},
            "issues_encountered": []
        }
        
        try:
            # Test 1: Error handling - User provides invalid input
            print("   👤 USER: Let me test what happens when I make a mistake...")
            factory = CharacterFactory()
            
            # Try to create a character that doesn't exist
            try:
                invalid_agent = factory.create_character("nonexistent_character_12345")
                results["usability_metrics"]["error_handling"] = "poor"  # Should have failed gracefully
                results["issues_encountered"].append("System accepted invalid character without proper error")
            except Exception as e:
                error_message = str(e)
                # Evaluate error message quality
                is_user_friendly = not any(technical in error_message.lower() for technical in 
                                         ["traceback", "exception", "stack", "null pointer", "__"])
                results["usability_metrics"]["error_handling"] = "good" if is_user_friendly else "poor"
                if not is_user_friendly:
                    results["issues_encountered"].append(f"Technical error message shown to user: {error_message}")
            
            results["steps_completed"].append("tested_error_handling")
            
            # Test 2: System feedback - Check if user gets appropriate feedback
            print("   👤 USER: Checking if I get proper feedback during normal operations...")
            characters = factory.list_available_characters()
            
            if len(characters) >= 2:
                # Test normal operation feedback
                director = DirectorAgent()
                agent1 = factory.create_character(characters[0])
                agent2 = factory.create_character(characters[1])
                director.register_agent(agent1)
                director.register_agent(agent2)
                story_result = director.run_turn()
                
                feedback_quality = {
                    "operation_completed": story_result is not None,
                    "result_structure_clear": isinstance(story_result, dict) and "content" in story_result,
                    "content_accessible": story_result and story_result.get("content", "").strip() != ""
                }
                
                results["usability_metrics"]["feedback_quality"] = feedback_quality
                results["steps_completed"].append("tested_system_feedback")
                
                # Test 3: Consistency - Multiple operations should behave consistently
                print("   👤 USER: Testing if the system behaves consistently...")
                consistent_results = []
                
                for i in range(3):
                    try:
                        director = DirectorAgent()
                        agent1 = factory.create_character(characters[0])
                        agent2 = factory.create_character(characters[1])
                        director.register_agent(agent1)
                        director.register_agent(agent2)
                        result = director.run_turn()
                        consistent_results.append({
                            "success": result is not None,
                            "has_content": result and "content" in result,
                            "content_quality": result and len(result.get("content", "")) > 50
                        })
                    except Exception:
                        consistent_results.append({"success": False, "has_content": False, "content_quality": False})
                
                # Evaluate consistency
                success_rates = [r["success"] for r in consistent_results]
                content_rates = [r["has_content"] for r in consistent_results]
                quality_rates = [r["content_quality"] for r in consistent_results]
                
                consistency_score = {
                    "success_consistency": sum(success_rates) / len(success_rates),
                    "content_consistency": sum(content_rates) / len(content_rates) if any(content_rates) else 0,
                    "quality_consistency": sum(quality_rates) / len(quality_rates) if any(quality_rates) else 0
                }
                
                results["usability_metrics"]["consistency"] = consistency_score
                results["steps_completed"].append("tested_consistency")
                
                # Overall usability assessment
                overall_usability = {
                    "error_handling_quality": results["usability_metrics"]["error_handling"],
                    "feedback_clarity": "good" if feedback_quality["result_structure_clear"] else "poor",
                    "system_reliability": "good" if consistency_score["success_consistency"] >= 0.8 else "poor",
                    "user_satisfaction": "satisfied"
                }
                
                # Determine user satisfaction based on metrics
                issues_found = []
                if overall_usability["error_handling_quality"] == "poor":
                    issues_found.append("Poor error handling and user feedback")
                if overall_usability["feedback_clarity"] == "poor":
                    issues_found.append("Unclear system feedback")
                if overall_usability["system_reliability"] == "poor":
                    issues_found.append("Inconsistent system behavior")
                
                if len(issues_found) == 0:
                    overall_usability["user_satisfaction"] = "very_satisfied"
                    self.user_feedback["overall"] = "The system is intuitive and reliable. Great user experience!"
                elif len(issues_found) <= 1:
                    overall_usability["user_satisfaction"] = "satisfied_with_minor_issues"
                    self.user_feedback["overall"] = f"Generally good usability with minor issues: {', '.join(issues_found)}"
                else:
                    overall_usability["user_satisfaction"] = "unsatisfied"
                    self.user_feedback["overall"] = f"Poor usability experience: {', '.join(issues_found)}"
                
                results["user_experience"]["overall_usability"] = overall_usability
                results["issues_encountered"].extend(issues_found)
                
            else:
                results["issues_encountered"].append("Not enough characters available to test system functionality")
                self.user_feedback["overall"] = "Cannot properly use the system due to insufficient characters."
                
        except Exception as e:
            results["issues_encountered"].append(f"Major system error during usability testing: {str(e)}")
            self.user_feedback["overall"] = f"System has serious usability problems: {str(e)}"
        
        return results
    
    def _evaluate_acceptance_criteria(self) -> bool:
        """Evaluate acceptance criteria from user perspective"""
        if not self.result or "error" in self.result:
            return False
        
        result = self.result
        
        criteria_met = 0
        total_criteria = len(self.acceptance_criteria)
        
        # Error handling quality
        if result.get("usability_metrics", {}).get("error_handling") == "good":
            criteria_met += 1
        
        # System feedback
        feedback = result.get("usability_metrics", {}).get("feedback_quality", {})
        if feedback.get("result_structure_clear", False):
            criteria_met += 1
        
        # Error recovery (tested through error handling)
        if "tested_error_handling" in result.get("steps_completed", []):
            criteria_met += 1
        
        # Performance (execution time)
        if self.execution_time and self.execution_time < 120:  # 2 minutes for usability test
            criteria_met += 1
        
        # Consistency
        consistency = result.get("usability_metrics", {}).get("consistency", {})
        if consistency.get("success_consistency", 0) >= 0.8:
            criteria_met += 1
        
        # Understandability (based on user satisfaction)
        overall = result.get("user_experience", {}).get("overall_usability", {})
        if overall.get("user_satisfaction") in ["satisfied", "very_satisfied", "satisfied_with_minor_issues"]:
            criteria_met += 1
        
        return criteria_met >= (total_criteria * 0.75)

class UATFramework:
    """User Acceptance Testing framework"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.uat_results = {
            "test_scenarios": [],
            "user_feedback_summary": {},
            "overall_acceptance": {},
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        self.test_scenarios = self._initialize_test_scenarios()
        
    def _initialize_test_scenarios(self) -> List[UserAcceptanceTest]:
        """Initialize UAT test scenarios"""
        return [
            StoryGenerationUAT(),
            CampaignManagementUAT(),
            SystemUsabilityUAT()
        ]
    
    def run_all_uat_scenarios(self) -> Dict[str, Any]:
        """Execute all UAT scenarios"""
        print("=== PHASE 5: USER ACCEPTANCE TESTING (UAT) ===\n")
        print("👤 Simulating real user workflows and experiences...\n")
        
        passed_scenarios = 0
        total_scenarios = len(self.test_scenarios)
        
        for i, scenario in enumerate(self.test_scenarios, 1):
            print(f"🎯 UAT Scenario {i}: {scenario.name}")
            print(f"   User Story: {scenario.user_story}")
            
            # Execute the scenario
            scenario_passed = scenario.execute(self)
            
            if scenario_passed:
                passed_scenarios += 1
                print(f"   ✅ UAT PASSED - User satisfied with functionality")
            else:
                print(f"   ❌ UAT FAILED - User requirements not met")
            
            if scenario.user_feedback.get("overall"):
                print(f"   💬 User Feedback: {scenario.user_feedback['overall']}")
            
            print(f"   ⏱️ Execution Time: {scenario.execution_time:.1f} seconds\n")
            
            # Store results
            self.uat_results["test_scenarios"].append(scenario.to_dict())
        
        # Generate summary
        self._generate_uat_summary(passed_scenarios, total_scenarios)
        
        # Generate recommendations
        self._generate_user_recommendations()
        
        # Save comprehensive report
        self._generate_uat_report()
        
        return self.uat_results
    
    def _generate_uat_summary(self, passed_scenarios: int, total_scenarios: int):
        """Generate UAT summary and overall acceptance"""
        acceptance_rate = passed_scenarios / total_scenarios
        
        overall_acceptance = {
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "acceptance_rate": acceptance_rate,
            "user_acceptance_status": self._determine_acceptance_status(acceptance_rate),
            "ready_for_production": acceptance_rate >= 0.8
        }
        
        # Collect user feedback themes
        user_feedback_themes = {
            "positive_feedback": [],
            "areas_for_improvement": [],
            "critical_issues": [],
            "user_satisfaction_levels": []
        }
        
        for scenario_result in self.uat_results["test_scenarios"]:
            feedback = scenario_result.get("user_feedback", {}).get("overall", "")
            
            # Analyze feedback sentiment and themes
            if "perfect" in feedback.lower() or "impressed" in feedback.lower() or "great" in feedback.lower():
                user_feedback_themes["positive_feedback"].append(scenario_result["name"])
            
            if "issues" in feedback.lower() or "problems" in feedback.lower():
                user_feedback_themes["areas_for_improvement"].append(scenario_result["name"])
            
            if "unacceptable" in feedback.lower() or "failed" in feedback.lower() or "crashed" in feedback.lower():
                user_feedback_themes["critical_issues"].append(scenario_result["name"])
            
            # Extract satisfaction level
            if "very_satisfied" in str(scenario_result.get("result", {})):
                user_feedback_themes["user_satisfaction_levels"].append("very_satisfied")
            elif "satisfied" in str(scenario_result.get("result", {})):
                user_feedback_themes["user_satisfaction_levels"].append("satisfied")
            else:
                user_feedback_themes["user_satisfaction_levels"].append("unsatisfied")
        
        self.uat_results["overall_acceptance"] = overall_acceptance
        self.uat_results["user_feedback_summary"] = user_feedback_themes
        
        # Print summary
        print("=== UAT SUMMARY ===")
        print(f"📊 Scenarios Passed: {passed_scenarios}/{total_scenarios} ({acceptance_rate:.1%})")
        print(f"🎯 User Acceptance Status: {overall_acceptance['user_acceptance_status']}")
        print(f"🚀 Ready for Production: {'✅ Yes' if overall_acceptance['ready_for_production'] else '❌ No'}")
        
        if user_feedback_themes["positive_feedback"]:
            print(f"👍 Positive User Experience: {', '.join(user_feedback_themes['positive_feedback'])}")
        
        if user_feedback_themes["critical_issues"]:
            print(f"🚨 Critical User Issues: {', '.join(user_feedback_themes['critical_issues'])}")
        
        print()
    
    def _determine_acceptance_status(self, acceptance_rate: float) -> str:
        """Determine overall user acceptance status"""
        if acceptance_rate >= 0.9:
            return "EXCELLENT - Users highly satisfied"
        elif acceptance_rate >= 0.8:
            return "GOOD - Users generally satisfied" 
        elif acceptance_rate >= 0.6:
            return "MARGINAL - Users have concerns"
        else:
            return "POOR - Users unsatisfied"
    
    def _generate_user_recommendations(self):
        """Generate recommendations from user perspective"""
        recommendations = []
        
        # Analyze common issues across scenarios
        all_issues = []
        for scenario_result in self.uat_results["test_scenarios"]:
            result = scenario_result.get("result", {})
            if isinstance(result, dict) and "issues_encountered" in result:
                all_issues.extend(result["issues_encountered"])
        
        # Generate recommendations based on common issues
        issue_counts = {}
        for issue in all_issues:
            for keyword in ["character", "unknown", "error", "slow", "crash", "format"]:
                if keyword in issue.lower():
                    issue_counts[keyword] = issue_counts.get(keyword, 0) + 1
        
        # Prioritize recommendations
        if issue_counts.get("unknown", 0) > 0:
            recommendations.append("HIGH PRIORITY: Eliminate all 'For Unknown' segments - users find this confusing and unprofessional")
        
        if issue_counts.get("character", 0) > 0:
            recommendations.append("HIGH PRIORITY: Improve character name integration - users expect their chosen characters to be prominently featured")
        
        if issue_counts.get("error", 0) > 0:
            recommendations.append("MEDIUM PRIORITY: Improve error handling and user feedback - users need clear, actionable error messages")
        
        if issue_counts.get("slow", 0) > 0:
            recommendations.append("MEDIUM PRIORITY: Optimize performance - users expect faster response times")
        
        if issue_counts.get("format", 0) > 0:
            recommendations.append("LOW PRIORITY: Improve output formatting - users want professional-looking narratives")
        
        # Add general recommendations based on acceptance rate
        acceptance_rate = self.uat_results["overall_acceptance"]["acceptance_rate"]
        if acceptance_rate < 0.8:
            recommendations.append("CRITICAL: System not ready for production deployment - address user concerns before release")
        
        if acceptance_rate < 0.6:
            recommendations.append("CRITICAL: Major usability overhaul needed - current system does not meet user needs")
        
        self.uat_results["recommendations"] = recommendations
        
        if recommendations:
            print("💡 USER-DRIVEN RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
            print()
    
    def _generate_uat_report(self):
        """Generate comprehensive UAT report"""
        report_path = os.path.join(self.project_root, "validation", "phase5_uat_report.json")
        
        # Save detailed report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.uat_results, f, indent=2)
        
        print(f"📄 Detailed UAT report saved to: {report_path}")


def main():
    """Run Phase 5 User Acceptance Testing"""
    try:
        print("StoryForge AI - Phase 5: User Acceptance Testing (UAT)")
        print("=" * 60)
        print("Simulating real user scenarios to validate system usability and acceptance")
        print()
        
        uat_framework = UATFramework()
        results = uat_framework.run_all_uat_scenarios()
        
        return results
        
    except Exception as e:
        print(f"❌ UAT framework error: {str(e)}")
        return None


if __name__ == "__main__":
    main()