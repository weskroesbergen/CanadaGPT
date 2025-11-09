/**
 * PostalCodeInput Component
 *
 * Validated input field for Canadian postal codes
 * with auto-formatting and error messages
 */

'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  validateCanadianPostalCode,
  formatPostalCode,
  getPostalCodeError
} from '@/lib/postalCodeUtils';

interface PostalCodeInputProps {
  value: string;
  onChange: (value: string) => void;
  onValidPostalCode?: (postalCode: string) => void;
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  className?: string;
  error?: string;
  showValidation?: boolean;
}

export function PostalCodeInput({
  value,
  onChange,
  onValidPostalCode,
  placeholder,
  disabled = false,
  autoFocus = false,
  className = '',
  error: externalError,
  showValidation = true
}: PostalCodeInputProps) {
  const t = useTranslations('mps.myMP');
  const [touched, setTouched] = useState(false);
  const [internalError, setInternalError] = useState<string>('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let inputValue = e.target.value.toUpperCase();

    // Remove any non-alphanumeric characters except spaces
    inputValue = inputValue.replace(/[^A-Z0-9\s]/g, '');

    // Auto-format as user types (add space after 3rd character)
    if (inputValue.length > 3 && !inputValue.includes(' ')) {
      inputValue = inputValue.slice(0, 3) + ' ' + inputValue.slice(3);
    }

    // Limit to 7 characters (A1A 1A1)
    if (inputValue.length > 7) {
      inputValue = inputValue.slice(0, 7);
    }

    onChange(inputValue);

    // Clear error when user starts typing
    if (internalError) {
      setInternalError('');
    }
  };

  const handleBlur = () => {
    setTouched(true);

    if (!value) {
      setInternalError('');
      return;
    }

    // Validate on blur
    if (!validateCanadianPostalCode(value)) {
      setInternalError(getPostalCodeError(value));
    } else {
      setInternalError('');

      // Format the postal code
      const formatted = formatPostalCode(value);
      if (formatted !== value) {
        onChange(formatted);
      }

      // Notify parent of valid postal code
      if (onValidPostalCode) {
        onValidPostalCode(formatted);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();

      if (validateCanadianPostalCode(value)) {
        const formatted = formatPostalCode(value);
        if (onValidPostalCode) {
          onValidPostalCode(formatted);
        }
      } else {
        setTouched(true);
        setInternalError(getPostalCodeError(value));
      }
    }
  };

  const displayError = externalError || (touched && showValidation ? internalError : '');
  const isValid = value && validateCanadianPostalCode(value);
  const showSuccess = touched && isValid && !displayError && showValidation;

  return (
    <div className={`relative ${className}`}>
      <input
        type="text"
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || t('postalCodePlaceholder')}
        disabled={disabled}
        autoFocus={autoFocus}
        className={`
          w-full px-4 py-2 rounded-md border
          ${displayError
            ? 'border-red-500 focus:border-red-500 focus:ring-red-500'
            : showSuccess
              ? 'border-green-500 focus:border-green-500 focus:ring-green-500'
              : 'border-gray-300 dark:border-gray-600 focus:border-blue-500 focus:ring-blue-500'
          }
          bg-white dark:bg-gray-800
          text-gray-900 dark:text-gray-100
          placeholder:text-gray-400 dark:placeholder:text-gray-500
          focus:outline-none focus:ring-2
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors
        `}
        aria-invalid={!!displayError}
        aria-describedby={displayError ? 'postal-code-error' : undefined}
      />

      {/* Success checkmark */}
      {showSuccess && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2">
          <svg
            className="w-5 h-5 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
      )}

      {/* Error message */}
      {displayError && (
        <p
          id="postal-code-error"
          className="mt-1 text-sm text-red-600 dark:text-red-400"
        >
          {displayError}
        </p>
      )}
    </div>
  );
}
