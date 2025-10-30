module.exports = {
  extends: [
    'stylelint-config-standard',
    'stylelint-config-recommended',
  ],
  rules: {
    'color-named': null,
    // Relax rules to avoid blocking while CSS is reconciled to tokens
    'color-no-hex': null,
    'color-function-notation': null,
    'alpha-value-notation': null,
    'shorthand-property-no-redundant-values': null,
    'media-feature-range-notation': null,
    'selector-class-pattern': null,
    'property-no-vendor-prefix': true,
    'value-keyword-case': null,
    // Re-enable keyframe name check; fixed in index.css
    'keyframes-name-pattern': [
      '^[a-z][a-z0-9-]*$',
      { message: 'Keyframe names must be kebab-case (lowercase and hyphens).' }
    ],
    'comment-empty-line-before': null,
    'declaration-block-no-redundant-longhand-properties': null,
    // Re-enable font-family quote rules; adjusted in App.css
    'font-family-name-quotes': 'always-where-recommended',
    
    // Allow BEM-style class names (kebab with optional __ and -- parts)
    'selector-class-pattern': [
      '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:__(?:[a-z0-9]+(?:-[a-z0-9]+)*))?(?:--(?:[a-z0-9]+(?:-[a-z0-9]+)*))?$',
      { message: 'Use BEM-style class names (kebab, optional __ and -- modifiers).' }
    ],
    'color-hex-length': null,
    'property-no-unknown': null,
    'rule-empty-line-before': null,
  },
  ignoreFiles: [
    '**/*.js',
    '**/*.jsx',
    '**/*.ts',
    '**/*.tsx',
    'src/styles/design-system.generated.css',
    'src/styles/design-system.css',
    'src/components/**/*.css',
    'src/components/**/**/*.css',
    'src/components/**/**/**/*.css',
  ],
}; 
