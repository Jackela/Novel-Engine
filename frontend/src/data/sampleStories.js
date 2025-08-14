/**
 * Sample Stories Database
 * 
 * Pre-generated story content for demo mode and onboarding
 * Features diverse genres, characters, and narrative styles
 * to showcase StoryForge AI capabilities without API requirements
 */

export const SAMPLE_STORIES = {
  space_explorer: {
    id: 'space_explorer',
    title: 'The Quantum Drift',
    genre: 'Science Fiction',
    theme: 'exploration',
    description: 'A space exploration mission encounters mysterious quantum anomalies',
    estimatedLength: '10-15 minutes',
    characters: [
      {
        name: 'Commander Sarah Chen',
        profession: 'Starship Commander',
        personality: 'Decisive leader with scientific curiosity',
        background: 'Former astrophysicist turned military commander'
      },
      {
        name: 'Dr. Malik Okafor',
        profession: 'Quantum Physicist',
        personality: 'Brilliant but cautious researcher',
        background: 'Expert in quantum mechanics and spacetime theory'
      },
      {
        name: 'Engineer Zara Kim',
        profession: 'Systems Engineer',
        personality: 'Practical problem-solver with dry humor',
        background: 'Veteran engineer with experience in hostile environments'
      }
    ],
    opening: {
      setting: "The starship Endeavor drifts through the Veil Nebula, its sensors detecting strange quantum signatures.",
      initialSituation: "Strange readings appear on the navigation console as space itself seems to ripple around the ship.",
      hook: "What appears to be a routine survey mission suddenly becomes something far more mysterious."
    },
    sampleTurns: [
      {
        turn: 1,
        narrator: "The bridge of the Endeavor hummed with tension as Commander Sarah Chen studied the impossible readings on her tactical display. The stars outside seemed to shimmer and bend, creating patterns that defied conventional physics.",
        characters: {
          'Commander Sarah Chen': {
            dialogue: "Dr. Okafor, I need an explanation for these readings. The navigation sensors are showing spatial distortions that shouldn't be possible.",
            action: "leans forward, gripping the command chair as she studies the swirling patterns on the main viewscreen",
            emotion: "focused concern"
          },
          'Dr. Malik Okafor': {
            dialogue: "Commander, these readings... they're consistent with quantum tunneling events, but on a massive scale. It's as if space itself is becoming unstable.",
            action: "rapidly calculates on his quantum scanner, his brow furrowed in concentration",
            emotion: "scientific excitement mixed with worry"
          },
          'Engineer Zara Kim': {
            dialogue: "Whatever's happening out there, it's playing havoc with our systems. Hull integrity is holding, but I'm seeing fluctuations in the quantum drive.",
            action: "monitors multiple engineering displays while making rapid adjustments to ship systems",
            emotion: "professional alertness"
          }
        },
        outcome: "The crew realizes they're dealing with unprecedented quantum phenomena that could either revolutionize science or destroy their ship."
      },
      {
        turn: 2,
        narrator: "As the crew debates their next move, the quantum distortions intensify. Through the viewscreen, they see what appears to be another version of their own ship, shimmering like a mirage in the cosmic void.",
        characters: {
          'Commander Sarah Chen': {
            dialogue: "That's impossible. Are we looking at some kind of reflection? Or...",
            action: "stands and approaches the viewscreen, her reflection mingling with the impossible sight before them",
            emotion: "awe and growing unease"
          },
          'Dr. Malik Okafor': {
            dialogue: "Not a reflection, Commander. If my calculations are correct, we're seeing a parallel quantum state of our own ship. Multiple realities are converging.",
            action: "pulls up holographic models showing intersecting probability waves",
            emotion: "intellectual excitement overriding caution"
          },
          'Engineer Zara Kim': {
            dialogue: "Great. So we're dealing with multiple versions of ourselves. Just what I needed to make this day complete.",
            action: "continues working at her station but glances nervously at the viewscreen",
            emotion: "sardonic acceptance of the absurd situation"
          }
        },
        outcome: "The crew must decide whether to investigate this quantum phenomenon or retreat to safety."
      }
    ],
    themes: ['exploration', 'science', 'teamwork', 'unknown'],
    mood: 'mysterious_hopeful',
    complexity: 'medium'
  },

  medieval_quest: {
    id: 'medieval_quest',
    title: 'The Scholar\'s Gambit',
    genre: 'Fantasy Adventure',
    theme: 'knowledge_vs_power',
    description: 'A scholar, knight, and merchant uncover ancient secrets in a medieval kingdom',
    estimatedLength: '12-18 minutes',
    characters: [
      {
        name: 'Elena Ravencrest',
        profession: 'Royal Scholar',
        personality: 'Intelligent and determined with hidden depths',
        background: 'Youngest appointed royal scholar, expert in ancient languages'
      },
      {
        name: 'Sir Marcus Ironhold',
        profession: 'Knight Protector',
        personality: 'Honor-bound but pragmatic warrior',
        background: 'Veteran knight sworn to protect the realm\'s knowledge'
      },
      {
        name: 'Tobias Quicksilver',
        profession: 'Master Merchant',
        personality: 'Charming negotiator with network of contacts',
        background: 'Successful trader with connections across the kingdom'
      }
    ],
    opening: {
      setting: "The Great Library of Aethermoor, where ancient tomes hold secrets that could reshape the kingdom.",
      initialSituation: "A mysterious manuscript surfaces, written in a script that predates the kingdom itself.",
      hook: "The manuscript contains references to a powerful artifact that could either save or doom the realm."
    },
    sampleTurns: [
      {
        turn: 1,
        narrator: "Dust motes danced in the golden afternoon light streaming through the Great Library's stained glass windows. Elena Ravencrest carefully unrolled the ancient parchment, its edges brittle with age.",
        characters: {
          'Elena Ravencrest': {
            dialogue: "This script... it's older than our oldest records. The symbols suggest it predates the founding of Aethermoor by centuries.",
            action: "traces the mysterious symbols with her finger, careful not to damage the delicate parchment",
            emotion: "scholarly excitement with underlying concern"
          },
          'Sir Marcus Ironhold': {
            dialogue: "Ancient or not, someone went to great lengths to ensure this manuscript reached us. The messenger bore the seal of the Northern Watchtowers.",
            action: "stands watchfully by the library entrance, hand resting on his sword hilt",
            emotion: "alert protectiveness"
          },
          'Tobias Quicksilver': {
            dialogue: "If the watchtowers are involved, this isn't just academic curiosity. They've been reporting strange lights in the northern mountains for weeks.",
            action: "examines the messenger's pouch, noting its unusual construction and materials",
            emotion: "calculating concern"
          }
        },
        outcome: "The trio realizes they're dealing with something far more significant than a simple historical document."
      },
      {
        turn: 2,
        narrator: "As Elena continues to decipher the ancient text, the symbols begin to glow with a faint blue light. The very air in the library seems to thrum with hidden energy.",
        characters: {
          'Elena Ravencrest': {
            dialogue: "By the ancients... the text is responding to my touch. It speaks of the Prism of Echoing Light - a relic that can reveal hidden truths.",
            action: "pulls her hand back as the glowing intensifies, then cautiously reaches out again",
            emotion: "wonder mixed with scholarly caution"
          },
          'Sir Marcus Ironhold': {
            dialogue: "If this relic reveals truths, then there are those who would kill to possess it - and others who would die to keep it hidden.",
            action: "draws his sword partway from its sheath as he scans the library shadows",
            emotion: "protective vigilance"
          },
          'Tobias Quicksilver': {
            dialogue: "The Northern Watchtowers, the glowing manuscript, strange lights in the mountains - the pieces are forming a picture I don't like.",
            action: "moves to secure the library doors while keeping watch on the windows",
            emotion: "growing unease and strategic thinking"
          }
        },
        outcome: "The manuscript reveals the location of an ancient relic, but also suggests they're not the only ones seeking it."
      }
    ],
    themes: ['knowledge', 'adventure', 'ancient_mysteries', 'friendship'],
    mood: 'mysterious_adventurous',
    complexity: 'medium'
  },

  modern_mystery: {
    id: 'modern_mystery',
    title: 'The Algorithm\'s Shadow',
    genre: 'Tech Thriller',
    theme: 'digital_privacy',
    description: 'A tech journalist, cybersecurity expert, and data analyst uncover a conspiracy',
    estimatedLength: '8-12 minutes',
    characters: [
      {
        name: 'Alex Rivera',
        profession: 'Investigative Journalist',
        personality: 'Persistent truth-seeker with ethical principles',
        background: 'Award-winning journalist specializing in technology and privacy'
      },
      {
        name: 'Sam Chen',
        profession: 'Cybersecurity Expert',
        personality: 'Methodical hacker with strong moral compass',
        background: 'Former government security specialist now working independently'
      },
      {
        name: 'Dr. Maya Patel',
        profession: 'Data Scientist',
        personality: 'Analytical thinker who sees patterns others miss',
        background: 'PhD in computer science with expertise in AI and data mining'
      }
    ],
    opening: {
      setting: "A modern coffee shop in the tech district, where encrypted messages and suspicious data patterns hide in plain sight.",
      initialSituation: "A whistleblower contacts the team about irregularities in a major social media platform's data handling.",
      hook: "Personal data from millions of users is being used for purposes far beyond what anyone consented to."
    },
    sampleTurns: [
      {
        turn: 1,
        narrator: "The Quantum Café buzzed with the usual mix of startup hopefuls and established tech workers. Alex Rivera sat in the corner booth, laptop open, reviewing encrypted files that could expose one of the biggest privacy scandals in tech history.",
        characters: {
          'Alex Rivera': {
            dialogue: "The data patterns you've uncovered are damning, Maya. This isn't just targeted advertising - they're building psychological profiles for manipulation.",
            action: "scrolls through spreadsheets while glancing nervously at other patrons",
            emotion: "determined outrage"
          },
          'Sam Chen': {
            dialogue: "I've traced the data flows. The information is being shared with third parties that have no business accessing personal conversations and private posts.",
            action: "types rapidly on a modified laptop with additional security hardware",
            emotion: "focused anger"
          },
          'Dr. Maya Patel': {
            dialogue: "The algorithmic analysis suggests they're not just collecting data - they're actively influencing user behavior to generate more valuable data points.",
            action: "overlays multiple data visualizations on her tablet, pointing to concerning patterns",
            emotion: "scientific concern for ethical implications"
          }
        },
        outcome: "The team realizes they're uncovering a systematic privacy violation affecting millions of users."
      },
      {
        turn: 2,
        narrator: "As the team delves deeper into the data, Sam's security software detects someone attempting to access their encrypted connection. The hunters have become the hunted.",
        characters: {
          'Alex Rivera': {
            dialogue: "We need to move. If they're tracking us, it means we're onto something big enough that they're willing to take risks to stop us.",
            action: "quickly saves files to an encrypted drive while preparing to leave",
            emotion: "urgency mixed with journalistic determination"
          },
          'Sam Chen': {
            dialogue: "They're using sophisticated intrusion techniques - this isn't amateur hour. We're dealing with people who have serious resources.",
            action: "initiates multiple security protocols while monitoring for additional intrusion attempts",
            emotion: "professional respect for the threat level"
          },
          'Dr. Maya Patel': {
            dialogue: "The timing of this intrusion correlates with our discovery of the manipulation algorithms. They know exactly what we've found.",
            action: "analyzes the intrusion patterns while backing up critical data to multiple secure locations",
            emotion: "analytical calm masking underlying worry"
          }
        },
        outcome: "The team must decide whether to publish immediately or gather more evidence while evading digital surveillance."
      }
    ],
    themes: ['privacy', 'technology', 'ethics', 'truth'],
    mood: 'tense_urgent',
    complexity: 'high'
  },

  detective_noir: {
    id: 'detective_noir',
    title: 'Shadows on Pier 47',
    genre: 'Crime Noir',
    theme: 'justice_corruption',
    description: 'A detective, forensic analyst, and informant investigate corruption in a gritty city',
    estimatedLength: '15-20 minutes',
    characters: [
      {
        name: 'Detective Ray Morrison',
        profession: 'Homicide Detective',
        personality: 'Cynical but principled, haunted by past cases',
        background: '20-year veteran of the police force with a reputation for integrity'
      },
      {
        name: 'Dr. Lisa Park',
        profession: 'Forensic Scientist',
        personality: 'Meticulous analyst who believes evidence never lies',
        background: 'Top forensic specialist with expertise in complex crime scenes'
      },
      {
        name: 'Tommy "The Wire" Castellano',
        profession: 'Street Informant',
        personality: 'Streetwise survivor with surprising loyalty',
        background: 'Former small-time criminal now working as a police informant'
      }
    ],
    opening: {
      setting: "The fog-shrouded docks of Harbor City, where legitimate business and criminal enterprise intermingle.",
      initialSituation: "A body is discovered at Pier 47 with evidence suggesting police involvement in the murder.",
      hook: "The victim was about to testify against corrupt officers in a major police misconduct case."
    },
    sampleTurns: [
      {
        turn: 1,
        narrator: "The morning fog clung to Pier 47 like a guilty secret. Detective Ray Morrison stood over the body, the harsh dock lights casting long shadows across the crime scene.",
        characters: {
          'Detective Ray Morrison': {
            dialogue: "Professional execution. Single shot to the back of the head. Whoever did this wanted to send a message.",
            action: "crouches beside the body, studying the positioning while careful not to disturb evidence",
            emotion: "grim professional focus"
          },
          'Dr. Lisa Park': {
            dialogue: "The forensics tell a story. Powder burns suggest close range, but the angle is wrong for suicide. This was definitely murder.",
            action: "carefully collects evidence while photographing the scene from multiple angles",
            emotion: "methodical determination"
          },
          'Tommy "The Wire" Castellano': {
            dialogue: "Word on the street is that Jimmy here was planning to sing to Internal Affairs about certain cops taking money from the Torrino family.",
            action: "keeps watch for approaching figures while nervously fidgeting with a cigarette",
            emotion: "anxious knowledge"
          }
        },
        outcome: "The evidence points toward police involvement, putting the investigation team in a dangerous position."
      },
      {
        turn: 2,
        narrator: "As the team processes the crime scene, a black sedan with tinted windows slowly cruises past the pier. The investigation has attracted unwanted attention.",
        characters: {
          'Detective Ray Morrison': {
            dialogue: "We've got company. That's the third time that sedan has driven by. Either we're being watched or warned.",
            action: "subtly positions himself to observe the vehicle while appearing to focus on the crime scene",
            emotion: "alert suspicion"
          },
          'Dr. Lisa Park': {
            dialogue: "I found something. The victim had a memory card hidden in his jacket lining. Whatever's on here might be worth killing for.",
            action: "carefully extracts the device using forensic tools, sealing it in an evidence bag",
            emotion: "excited apprehension"
          },
          'Tommy "The Wire" Castellano': {
            dialogue: "We need to move this along. The longer we stay here, the more likely someone's going to decide we know too much.",
            action: "glances nervously between the crime scene and the street, ready to run if necessary",
            emotion: "street-smart fear"
          }
        },
        outcome: "The discovery of hidden evidence increases both the potential for justice and the danger to the investigation team."
      }
    ],
    themes: ['justice', 'corruption', 'loyalty', 'truth'],
    mood: 'dark_gritty',
    complexity: 'high'
  },

  romantic_adventure: {
    id: 'romantic_adventure',
    title: 'The Painter\'s Map',
    genre: 'Romantic Adventure',
    theme: 'love_discovery',
    description: 'An art restorer, travel photographer, and historian search for a lost masterpiece',
    estimatedLength: '10-14 minutes',
    characters: [
      {
        name: 'Isabella Romano',
        profession: 'Art Restorer',
        personality: 'Passionate about art with a romantic soul',
        background: 'Renowned specialist in Renaissance art from a family of Italian artists'
      },
      {
        name: 'Marcus Sullivan',
        profession: 'Travel Photographer',
        personality: 'Adventurous spirit with an eye for beauty',
        background: 'Award-winning photographer who documents hidden places around the world'
      },
      {
        name: 'Professor Elena Vasquez',
        profession: 'Art Historian',
        personality: 'Scholarly wisdom combined with romantic idealism',
        background: 'Expert in lost artworks and the stories behind them'
      }
    ],
    opening: {
      setting: "A charming art restoration studio in Florence, where old paintings reveal new secrets.",
      initialSituation: "Hidden beneath layers of paint, a restoration reveals clues to a lost masterpiece's location.",
      hook: "The painting contains a coded map leading to a work thought destroyed centuries ago."
    },
    sampleTurns: [
      {
        turn: 1,
        narrator: "Golden afternoon light streamed through the tall windows of Isabella's restoration studio. The scent of linseed oil and aged canvas filled the air as she carefully removed centuries of overpainting from a small portrait.",
        characters: {
          'Isabella Romano': {
            dialogue: "Marcus, look at this! Beneath the Victorian portrait, there are symbols - they're definitely Renaissance-era, but they're not decorative. They're intentional.",
            action: "uses a delicate brush to reveal more of the hidden layer, her eyes bright with discovery",
            emotion: "excited fascination"
          },
          'Marcus Sullivan': {
            dialogue: "Those symbols... they remind me of something I photographed in a monastery in Tuscany. The same geometric patterns carved into a chapel wall.",
            action: "pulls up photos on his camera, comparing them to the revealed symbols",
            emotion: "intrigued recognition"
          },
          'Professor Elena Vasquez': {
            dialogue: "If I'm right about this, you've uncovered part of a map system created by artists during the Renaissance to hide their most precious works from war and theft.",
            action: "examines the symbols through a magnifying glass while consulting historical texts",
            emotion: "scholarly excitement"
          }
        },
        outcome: "The trio realizes they've discovered the first clue to finding a lost masterpiece."
      },
      {
        turn: 2,
        narrator: "As the symbols are fully revealed, they form a partial map of the Tuscan countryside. The team realizes they're looking at directions to something that has been hidden for over four hundred years.",
        characters: {
          'Isabella Romano': {
            dialogue: "The detail is extraordinary. This isn't just a map - it's a love letter. See how the artist painted these tiny flowers? They match the ones in his portrait of Maria de' Medici.",
            action: "traces the delicate details with wonder, completely absorbed in the artistic romance",
            emotion: "romantic wonder"
          },
          'Marcus Sullivan': {
            dialogue: "I know that landscape. Those hills, that distinctive rock formation - it's about fifty kilometers north of here. We could be there by sunset.",
            action: "spreads out modern maps beside the painting, correlating geographical features",
            emotion: "adventurous enthusiasm"
          },
          'Professor Elena Vasquez': {
            dialogue: "According to my research, the artist hid his greatest work when Florence was under siege. If this map is authentic, we could discover a painting the world thought was lost forever.",
            action: "cross-references historical documents with the revealed symbols",
            emotion: "historical significance and romance"
          }
        },
        outcome: "The team prepares for a journey that could lead to both artistic discovery and personal connection."
      }
    ],
    themes: ['love', 'art', 'adventure', 'discovery'],
    mood: 'romantic_adventurous',
    complexity: 'medium'
  }
};

/**
 * Character Personality Templates
 * Used for algorithmic character decisions in demo mode
 */
export const CHARACTER_TEMPLATES = {
  leader: {
    traits: ['decisive', 'responsible', 'protective'],
    decisionPatterns: ['analyze situation', 'consider team safety', 'take charge'],
    communicationStyle: 'direct and confident'
  },
  intellectual: {
    traits: ['analytical', 'curious', 'methodical'],
    decisionPatterns: ['gather information', 'analyze patterns', 'propose logical solutions'],
    communicationStyle: 'precise and detailed'
  },
  practical: {
    traits: ['resourceful', 'pragmatic', 'solution-oriented'],
    decisionPatterns: ['assess resources', 'find practical solutions', 'act efficiently'],
    communicationStyle: 'straightforward and action-focused'
  },
  creative: {
    traits: ['intuitive', 'artistic', 'emotionally aware'],
    decisionPatterns: ['consider emotional impact', 'think outside the box', 'value beauty and meaning'],
    communicationStyle: 'expressive and thoughtful'
  },
  streetwise: {
    traits: ['cautious', 'experienced', 'survival-focused'],
    decisionPatterns: ['assess danger', 'use street knowledge', 'prioritize safety'],
    communicationStyle: 'direct and realistic'
  }
};

/**
 * Story Generation Utilities
 */
export const STORY_UTILS = {
  /**
   * Get a random sample story
   */
  getRandomStory() {
    const storyIds = Object.keys(SAMPLE_STORIES);
    const randomId = storyIds[Math.floor(Math.random() * storyIds.length)];
    return SAMPLE_STORIES[randomId];
  },

  /**
   * Get stories by genre
   */
  getStoriesByGenre(genre) {
    return Object.values(SAMPLE_STORIES).filter(story => 
      story.genre.toLowerCase().includes(genre.toLowerCase())
    );
  },

  /**
   * Get stories by complexity
   */
  getStoriesByComplexity(complexity) {
    return Object.values(SAMPLE_STORIES).filter(story => 
      story.complexity === complexity
    );
  },

  /**
   * Get stories by theme
   */
  getStoriesByTheme(theme) {
    return Object.values(SAMPLE_STORIES).filter(story => 
      story.themes.includes(theme)
    );
  },

  /**
   * Generate character decision based on template
   */
  generateCharacterDecision(character, situation, template) {
    const characterTemplate = CHARACTER_TEMPLATES[template] || CHARACTER_TEMPLATES.practical;
    
    // Simple algorithmic decision making based on character traits
    const decisions = characterTemplate.decisionPatterns;
    const selectedDecision = decisions[Math.floor(Math.random() * decisions.length)];
    
    return {
      action: `${character.name} decides to ${selectedDecision}`,
      reasoning: `Based on ${character.name}'s ${characterTemplate.traits.join(', ')} nature`,
      dialogue: `"${this.generateDialogue(character, situation, characterTemplate)}"`
    };
  },

  /**
   * Generate simple dialogue based on character and situation
   */
  generateDialogue(character, situation, template) {
    const dialogueTemplates = {
      leader: [
        "We need to assess our options carefully.",
        "I'll take responsibility for this decision.",
        "Let's focus on what we can control."
      ],
      intellectual: [
        "The evidence suggests we should consider...",
        "Based on my analysis, I believe...",
        "There are several factors we need to examine."
      ],
      practical: [
        "Here's what we need to do right now.",
        "Let's focus on solving the immediate problem.",
        "We can figure out the details as we go."
      ],
      creative: [
        "I have a feeling about this situation.",
        "There might be something we're not seeing.",
        "Let's think about this differently."
      ],
      streetwise: [
        "Something doesn't feel right about this.",
        "We need to watch our backs here.",
        "Trust me, I've seen this before."
      ]
    };

    const characterType = Object.keys(CHARACTER_TEMPLATES).find(type => 
      CHARACTER_TEMPLATES[type] === template
    ) || 'practical';

    const templates = dialogueTemplates[characterType];
    return templates[Math.floor(Math.random() * templates.length)];
  }
};

export default SAMPLE_STORIES;