/**
 * MobileBillCard - Compact Bill Card for Lists
 */

'use client';

import React from 'react';
import { useRouter } from 'next/navigation';

interface MobileBillCardProps {
  bill: {
    number: string;
    session: string;
    title: string;
    status?: string;
    progress?: number;
  };
  locale?: string;
}

export function MobileBillCard({ bill, locale = 'en' }: MobileBillCardProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/${locale}/bills/${bill.session}/${bill.number}`);
  };

  const getStatusClass = (status?: string) => {
    if (!status) return '';
    const statusLower = status.toLowerCase();
    if (statusLower.includes('passed') || statusLower.includes('royal assent')) {
      return 'passed';
    }
    if (statusLower.includes('defeated') || statusLower.includes('withdrawn')) {
      return 'failed';
    }
    return 'active';
  };

  return (
    <div className="mobile-bill-card" onClick={handleClick}>
      <div className="mobile-bill-header">
        <div className="mobile-bill-number">{bill.number}</div>
        {bill.status && (
          <div className={`mobile-bill-status ${getStatusClass(bill.status)}`}>
            {bill.status}
          </div>
        )}
      </div>

      <h3 className="mobile-bill-title">{bill.title}</h3>

      {bill.progress !== undefined && (
        <div className="mobile-bill-progress">
          <div className="mobile-bill-progress-bar">
            <div
              className="mobile-bill-progress-fill"
              style={{ width: `${bill.progress}%` }}
            />
          </div>
          <div className="mobile-bill-progress-label">
            {bill.progress}% complete
          </div>
        </div>
      )}
    </div>
  );
}
