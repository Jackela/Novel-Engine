// Constraints utility for consistent validation across the frontend
import constraints from '../../src/constraints.json';

/**
 * Get character name validation constraints
 * @returns {Object} Character name constraints
 */
export const getNameConstraints = () => constraints.character.name;

/**
 * Get character description validation constraints  
 * @returns {Object} Character description constraints
 */
export const getDescriptionConstraints = () => constraints.character.description;

/**
 * Get file upload constraints
 * @returns {Object} File upload constraints
 */
export const getFileConstraints = () => constraints.file.upload;

/**
 * Get character selection constraints
 * @returns {Object} Character selection constraints
 */
export const getSelectionConstraints = () => constraints.simulation.characters;

/**
 * Get API configuration
 * @returns {Object} API configuration
 */
export const getApiConfig = () => constraints.api;

/**
 * Validate character name according to constraints
 * @param {string} name - Character name to validate
 * @returns {Object} Validation result with isValid and error message
 */
export const validateCharacterName = (name) => {
  const nameConstraints = getNameConstraints();
  
  if (!name || !name.trim()) {
    return { isValid: false, error: 'nameRequired' };
  }
  
  if (name.length < nameConstraints.minLength || name.length > nameConstraints.maxLength) {
    return { 
      isValid: false, 
      error: 'nameLength',
      params: { 
        min: nameConstraints.minLength, 
        max: nameConstraints.maxLength 
      }
    };
  }
  
  const pattern = new RegExp(nameConstraints.pattern);
  if (!pattern.test(name)) {
    return { isValid: false, error: 'pattern' };
  }
  
  return { isValid: true };
};

/**
 * Validate character description according to constraints
 * @param {string} description - Character description to validate
 * @returns {Object} Validation result with isValid and error message
 */
export const validateCharacterDescription = (description) => {
  const descConstraints = getDescriptionConstraints();
  
  if (!description || !description.trim()) {
    return { isValid: false, error: 'descriptionRequired' };
  }
  
  if (description.length < descConstraints.minLength || description.length > descConstraints.maxLength) {
    return { 
      isValid: false, 
      error: 'descriptionLength',
      params: { 
        min: descConstraints.minLength, 
        max: descConstraints.maxLength 
      }
    };
  }
  
  const wordCount = description.trim().split(/\s+/).length;
  if (wordCount < descConstraints.minWords) {
    return { 
      isValid: false, 
      error: 'descriptionWords',
      params: { min: descConstraints.minWords }
    };
  }
  
  return { isValid: true };
};

/**
 * Validate file upload according to constraints
 * @param {File} file - File to validate
 * @returns {Object} Validation result with isValid and error message
 */
export const validateFileUpload = (file) => {
  const fileConstraints = getFileConstraints();
  
  if (file.size > fileConstraints.maxSize) {
    return { 
      isValid: false, 
      error: 'fileSize',
      params: { 
        filename: file.name,
        max: fileConstraints.maxSizeMB 
      }
    };
  }
  
  const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
  if (!fileConstraints.allowedTypes.includes(fileExtension)) {
    return { 
      isValid: false, 
      error: 'fileType',
      params: { 
        filename: file.name,
        types: fileConstraints.allowedTypes.join(', ')
      }
    };
  }
  
  return { isValid: true };
};

/**
 * Validate character selection count according to constraints
 * @param {number} count - Number of selected characters
 * @returns {Object} Validation result with isValid and error message
 */
export const validateCharacterSelection = (count) => {
  const selectionConstraints = getSelectionConstraints();
  
  if (count < selectionConstraints.minSelection) {
    return { 
      isValid: false, 
      error: 'minSelection',
      params: { min: selectionConstraints.minSelection }
    };
  }
  
  if (count > selectionConstraints.maxSelection) {
    return { 
      isValid: false, 
      error: 'maxSelection',
      params: { max: selectionConstraints.maxSelection }
    };
  }
  
  return { isValid: true };
};

// Export all constraints for direct access
export default constraints;