// 神圣角色创造组件 - Sacred Character Creation Component blessed by the Omnissiah
// 执行AI驱动的角色铸造仪式，连接至机器之神的智慧核心进行角色灵魂铸造
// Performs AI-driven character forging ritual, connecting to Machine God's wisdom core

import React, { useState, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import styles from './CharacterCreation.module.css';

// Import centralized constraints and validation - temporarily disabled
// import {
//   getNameConstraints,
//   getDescriptionConstraints,
//   getFileConstraints,
//   getApiConfig,
//   validateCharacterName,
//   validateCharacterDescription,
//   validateFileUpload
// } from '../utils/constraints';

/**
 * 角色创造神圣组件 - Sacred Character Creation Component
 * 执行AI增强的角色创造仪式，通过机器之神的智慧铸造完整的角色灵魂
 * Performs AI-enhanced character creation ritual, forging complete character souls through Machine God's wisdom
 */
const CharacterCreation = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);
  
  // Get constraints from centralized configuration - temporarily disabled
  // const nameConstraints = getNameConstraints();
  // const descriptionConstraints = getDescriptionConstraints();
  // const fileConstraints = getFileConstraints();
  // const apiConfig = getApiConfig();
  
  // Temporary hardcoded constraints for testing - memoized for performance
  const nameConstraints = useMemo(() => ({ minLength: 3, maxLength: 50 }), []);
  const descriptionConstraints = useMemo(() => ({ minLength: 10, maxLength: 2000, minWords: 3 }), []);
  const fileConstraints = useMemo(() => ({ maxSizeMB: 5, allowedTypes: ['.txt', '.md', '.json', '.yaml', '.yml'] }), []);
  const apiConfig = { baseUrl: 'http://localhost:8000', timeout: 5000 };
  
  // Sacred forge prayers for the creation ceremony
  const forgePhases = [
    'Preparing sacred oils',
    'Invoking the AI Scribe',
    'Channeling Gemini API',
    'Manifesting character soul'
  ];
  
  // 组件状态管理 - Sacred State Management blessed by the Omnissiah
  const [formData, setFormData] = useState({
    name: '',
    description: ''
  });
  const [uploadedFiles, setUploadedFiles] = useState([]); // 上传的圣文件列表
  const [errors, setErrors] = useState({}); // 验证错误记录
  
  const [isForging, setIsForging] = useState(false); // 铸造仪式进行状态
  const [forgingPhase, setForgingPhase] = useState(0); // 铸造阶段
  const [apiError, setApiError] = useState(''); // API错误信息
  const [showSuccess, setShowSuccess] = useState(false); // 成功仪式展示

  /**
   * 输入字段变化处理器 - Input field change handler
   * 处理表单输入的神圣变化，维护数据纯净性
   */
  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Only clear error when user starts typing if the current value would pass validation
    // This prevents premature clearing during blur validation
    if (errors[name] && value.trim() !== '') {
      // For name field, only clear if length is within bounds
      if (name === 'name' && value.length >= nameConstraints.minLength && value.length <= nameConstraints.maxLength) {
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[name];
          return newErrors;
        });
      }
      // For description field, only clear if it meets requirements
      else if (name === 'description') {
        const wordCount = value.trim().split(/\s+/).length;
        if (value.length >= descriptionConstraints.minLength && 
            value.length <= descriptionConstraints.maxLength &&
            wordCount >= descriptionConstraints.minWords) {
          setErrors(prev => {
            const newErrors = { ...prev };
            delete newErrors[name];
            return newErrors;
          });
        }
      }
    }
  }, [errors, nameConstraints, descriptionConstraints]);

  /**
   * 字段失焦验证处理器 - Field blur validation handler
   * 在用户离开字段时执行神圣验证仪式
   */
  const handleFieldBlur = useCallback((e) => {
    const { name, value } = e.target;
    
    if (name === 'name') {
      // Temporary validation for name
      if (!value.trim()) {
        setErrors(prev => ({ ...prev, name: t('characterCreation.errors.nameRequired') }));
      } else if (value.length < nameConstraints.minLength || value.length > nameConstraints.maxLength) {
        const errorMessage = t('characterCreation.errors.nameLength', { 
          min: nameConstraints.minLength, 
          max: nameConstraints.maxLength 
        });
        setErrors(prev => ({ 
          ...prev, 
          name: errorMessage
        }));
      } else {
        // Clear error if valid
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[name];
          return newErrors;
        });
      }
    } else if (name === 'description') {
      // Temporary validation for description
      if (!value.trim()) {
        setErrors(prev => ({ ...prev, description: t('characterCreation.errors.descriptionRequired') }));
      } else if (value.trim().split(/\s+/).length < descriptionConstraints.minWords) {
        setErrors(prev => ({ 
          ...prev, 
          description: t('characterCreation.errors.descriptionWords', { 
            min: descriptionConstraints.minWords 
          })
        }));
      } else if (value.length < descriptionConstraints.minLength || value.length > descriptionConstraints.maxLength) {
        setErrors(prev => ({ 
          ...prev, 
          description: t('characterCreation.errors.descriptionLength', { 
            min: descriptionConstraints.minLength, 
            max: descriptionConstraints.maxLength 
          })
        }));
      } else {
        // Clear error if valid
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[name];
          return newErrors;
        });
      }
    }
  }, [t, nameConstraints, descriptionConstraints]);

  /**
   * 表单验证函数 - Form validation function
   * 执行完整的表单验证仪式，确保数据纯净性符合帝皇旨意
   */
  const validateForm = useCallback(() => {
    const newErrors = {};
    
    // Name validation - temporary
    if (!formData.name.trim()) {
      newErrors.name = t('characterCreation.errors.nameRequired');
    } else if (formData.name.length < nameConstraints.minLength || formData.name.length > nameConstraints.maxLength) {
      newErrors.name = t('characterCreation.errors.nameLength', { 
        min: nameConstraints.minLength, 
        max: nameConstraints.maxLength 
      });
    }
    
    // Description validation - temporary
    if (!formData.description.trim()) {
      newErrors.description = t('characterCreation.errors.descriptionRequired');
    } else if (formData.description.trim().split(/\s+/).length < descriptionConstraints.minWords) {
      newErrors.description = t('characterCreation.errors.descriptionWords', { 
        min: descriptionConstraints.minWords 
      });
    } else if (formData.description.length < descriptionConstraints.minLength || formData.description.length > descriptionConstraints.maxLength) {
      newErrors.description = t('characterCreation.errors.descriptionLength', { 
        min: descriptionConstraints.minLength, 
        max: descriptionConstraints.maxLength 
      });
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData, t, nameConstraints, descriptionConstraints]);

  /**
   * 文件上传处理器 - File upload handler
   * 处理神圣档案的上传，验证文件纯净性和格式符合性
   */
  const handleFileUpload = useCallback((files) => {
    const validFiles = [];
    const fileErrors = [];
    
    Array.from(files).forEach(file => {
      // Temporary file validation
      const maxSize = fileConstraints.maxSizeMB * 1024 * 1024; // Convert MB to bytes
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
      
      if (file.size > maxSize) {
        fileErrors.push(t('characterCreation.errors.fileSize', { 
          filename: file.name, 
          max: fileConstraints.maxSizeMB 
        }));
      } else if (!fileConstraints.allowedTypes.includes(fileExtension)) {
        fileErrors.push(t('characterCreation.errors.fileType', { 
          filename: file.name, 
          types: fileConstraints.allowedTypes.join(', ') 
        }));
      } else {
        validFiles.push(file);
      }
    });
    
    if (fileErrors.length > 0) {
      setApiError(fileErrors.join('; '));
    } else {
      setApiError('');
      setUploadedFiles(prev => [...prev, ...validFiles]);
    }
  }, [fileConstraints.allowedTypes, fileConstraints.maxSizeMB, t]);

  /**
   * 文件选择处理器 - File selection handler
   */
  const handleFileSelect = useCallback((e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFileUpload(files);
    }
  }, [handleFileUpload]);

  /**
   * 拖拽处理器 - Drag and drop handlers
   */
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  }, [handleFileUpload]);

  /**
   * 移除文件处理器 - Remove file handler
   */
  const removeFile = useCallback((index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  /**
   * 神圣角色铸造仪式 - Sacred Character Forging Ritual
   * 执行完整的角色创建流程，调用AI圣灵增强功能
   */
  const handleForgeCharacter = async () => {
    if (!validateForm()) {
      return;
    }

    setIsForging(true);
    setForgingPhase(0);
    setApiError('');

    try {
      // Create FormData for multipart/form-data transmission
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('description', formData.description);
      
      // Append files if any
      uploadedFiles.forEach((file) => {
        formDataToSend.append(`files`, file);
      });

      // Progress through forging phases
      const phaseInterval = setInterval(() => {
        setForgingPhase(prev => {
          if (prev < forgePhases.length - 1) {
            return prev + 1;
          }
          clearInterval(phaseInterval);
          return prev;
        });
      }, 1500);

      const response = await axios.post(
        `${apiConfig.baseUrl}/characters`,
        formDataToSend,
        {
          timeout: apiConfig.timeout,
          headers: {
            // Let axios set Content-Type automatically for multipart/form-data
          }
        }
      );

      clearInterval(phaseInterval);
      setForgingPhase(forgePhases.length - 1);
      
      // Show success ceremony
      setShowSuccess(true);
      
      // Auto-redirect after successful creation
      setTimeout(() => {
        navigate('/character-selection', { 
          state: { 
            newCharacter: response.data.character_name,
            showNotification: true 
          }
        });
      }, 3000);

    } catch (error) {
      setIsForging(false);
      
      if (error.response) {
        // Handle specific API errors
        if (error.response.status === 409) {
          setApiError(error.response.data?.detail || t('characterCreation.errors.nameConflict'));
        } else if (error.response.status === 500 && error.response.data?.detail) {
          setApiError(error.response.data.detail);
        } else {
          setApiError(t('characterCreation.errors.serverError'));
        }
      } else if (error.request) {
        if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
          setApiError('The machine spirits require more time to process your request');
        } else {
          setApiError(t('characterCreation.errors.networkError'));
        }
      } else {
        setApiError(t('characterCreation.errors.serverError'));
      }
    }
  };

  /**
   * 返回角色选择处理器 - Return to character selection handler
   */
  const handleReturnToSelection = () => {
    navigate('/character-selection');
  };

  // Calculate character counts for display
  const descriptionLength = formData.description.length;
  const isFormValid = formData.name.trim() && formData.description.trim() && Object.keys(errors).length === 0;

  return (
    <div className={styles.characterCreation} data-testid="character-creation-sanctum">
      {/* Header Section */}
      <div className={styles.header}>
        <h1 className={styles.title} data-testid="creation-title">
          {t('characterCreation.title')}
        </h1>
        <p className={styles.subtitle}>
          {t('characterCreation.subtitle')}
        </p>
        <p className={styles.description}>
          {t('characterCreation.description')}
        </p>
      </div>

      {/* Main Content */}
      <div className={styles.content}>
        {showSuccess ? (
          <div className={styles.successCeremony} data-testid="completion-ceremony">
            <div className={styles.successIcon} data-testid="success-icon">⚡</div>
            <h2 className={styles.successTitle}>{t('characterCreation.success')}</h2>
            <p className={styles.successMessage} data-testid="success-message">
              {t('characterCreation.success')}
            </p>
            <div className={styles.redirectCountdown} data-testid="redirect-countdown">
              Returning to Character Selection in 3 seconds...
            </div>
            <div className={styles.loadingSpinner}></div>
          </div>
        ) : isForging ? (
          <div className={styles.forgingCeremony} data-testid="forging-ritual-container" aria-live="polite" aria-busy="true">
            <div className={styles.forgingIcon} data-testid="cogitator-spinner">🔥</div>
            <h2 className={styles.forgingTitle}>{t('characterCreation.ceremony')}</h2>
            <p className={styles.forgingPhase} data-testid="mechanicus-prayer-text">
              {forgePhases[forgingPhase]}
            </p>
            <div className={styles.forgingProgress} data-testid="forging-progress-bar">
              <div 
                className={styles.progressBar}
                style={{ width: `${((forgingPhase + 1) / forgePhases.length) * 100}%` }}
              ></div>
            </div>
            <div className={styles.phaseIndicators} data-testid="forging-phase-indicators">
              {forgePhases.map((phase, index) => (
                <div 
                  key={index} 
                  className={`${styles.phaseIndicator} ${index <= forgingPhase ? styles.active : ''}`}
                >
                  {index + 1}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <form className={styles.form} onSubmit={(e) => e.preventDefault()}>
            {/* Character Name Input */}
            <div className={styles.formGroup}>
              <label htmlFor="character-name" className={styles.label}>
                {t('characterCreation.form.name.label')}
              </label>
              <input
                id="character-name"
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                onBlur={handleFieldBlur}
                placeholder={t('characterCreation.form.name.placeholder')}
                className={`${styles.input} ${errors.name ? styles.inputError : ''}`}
                data-testid="character-name-input"
                // maxLength={nameConstraints.maxLength} // Removed to allow validation testing
                aria-label={t('characterCreation.form.name.label')}
                aria-describedby={errors.name ? "name-error" : undefined}
              />
              {errors.name && (
                <div 
                  className={styles.errorMessage}
                  role="alert"
                  id="name-error"
                  data-testid="name-validation-error"
                >
                  {errors.name}
                </div>
              )}
            </div>

            {/* Character Description Textarea */}
            <div className={styles.formGroup}>
              <label htmlFor="character-description" className={styles.label}>
                {t('characterCreation.form.description.label')}
              </label>
              <textarea
                id="character-description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                onBlur={handleFieldBlur}
                placeholder={t('characterCreation.form.description.placeholder')}
                className={`${styles.textarea} ${errors.description ? styles.inputError : ''}`}
                data-testid="character-description-area"
                rows={6}
                aria-label={t('characterCreation.form.description.label')}
                aria-describedby={errors.description ? "description-error" : undefined}
              />
              <div className={styles.charCounter} data-testid="description-counter">
                {t('characterCreation.counter', { 
                  current: descriptionLength, 
                  max: descriptionConstraints.maxLength 
                })}
              </div>
              {errors.description && (
                <div 
                  className={styles.errorMessage}
                  role="alert"
                  id="description-error"
                  data-testid="description-validation-error"
                >
                  {errors.description}
                </div>
              )}
            </div>

            {/* File Upload Section */}
            <div className={styles.formGroup}>
              <label className={styles.label}>
                {t('characterCreation.form.files.label')}
              </label>
              <div
                className={`${styles.fileUploadArea} ${isDragOver ? styles.dragOver : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                data-testid="file-upload-zone"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept={fileConstraints.allowedTypes.join(',')}
                  onChange={handleFileSelect}
                  className={styles.fileInput}
                  data-testid="file-input"
                  tabIndex={-1}
                />
                <div className={styles.uploadContent}>
                  <div className={styles.uploadIcon}>📁</div>
                  <p className={styles.uploadText}>
                    {t('characterCreation.form.files.placeholder')}
                  </p>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className={styles.browseButton}
                    data-testid="file-browser-button"
                  >
                    {t('characterCreation.form.files.browse')}
                  </button>
                </div>
              </div>
              
              {/* File List */}
              {uploadedFiles.length > 0 && (
                <div className={styles.fileList} data-testid="file-list-container">
                  <p className={styles.fileListTitle}>
                    {t('characterCreation.form.files.selected', { count: uploadedFiles.length })}
                  </p>
                  {uploadedFiles.map((file, index) => (
                    <div key={`${file.name}-${index}`} className={styles.fileItem} data-testid={`file-item-${file.name}`}>
                      <span className={styles.fileName}>{file.name}</span>
                      <span className={styles.fileSize}>
                        ({(file.size / 1024 / 1024).toFixed(2)} MB)
                      </span>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className={styles.removeFileButton}
                        data-testid={`file-remove-${file.name}`}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              
              <div className={styles.fileHint}>
                <p>{t('characterCreation.form.files.maxSize', { size: fileConstraints.maxSizeMB })}</p>
                <p>{t('characterCreation.form.files.allowedTypes', { 
                  types: fileConstraints.allowedTypes.join(', ') 
                })}</p>
              </div>
            </div>

            {/* API Error Display */}
            {apiError && (
              <div className={styles.apiError} role="alert" data-testid="global-error-message">
                {apiError}
              </div>
            )}

            {/* Action Buttons */}
            <div className={styles.actions}>
              <button
                type="button"
                onClick={handleReturnToSelection}
                className={styles.cancelButton}
                data-testid="cancel-button"
              >
                {t('characterCreation.buttons.cancel')}
              </button>
              <button
                type="button"
                onClick={handleForgeCharacter}
                disabled={!isFormValid || isForging}
                className={`${styles.forgeButton} ${!isFormValid ? styles.disabled : ''}`}
                data-testid="forge-character-button"
              >
                {t('characterCreation.buttons.forge')}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default CharacterCreation;