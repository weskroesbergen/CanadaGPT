/**
 * GraphQL queries for Order Paper GANTT visualization
 */

import { gql } from '@apollo/client';

export const GET_ORDER_PAPER_GANTT = gql`
  query GetOrderPaperGantt($session: String!) {
    searchBills(
      session: $session
      limit: 100
    ) {
      number
      session
      title
      title_fr
      status
      status_fr
      bill_type
      bill_type_fr
      is_government_bill
      originating_chamber
      originating_chamber_fr
      introduced_date
      stage
      latest_event
      # Timeline dates for GANTT visualization
      passed_house_first_reading
      passed_house_second_reading
      passed_house_third_reading
      passed_senate_first_reading
      passed_senate_second_reading
      passed_senate_third_reading
      royal_assent_date
      # Committee referrals (for branching visual)
      referredTo {
        code
        name
      }
      # Sponsor info for hover
      sponsor {
        name
        party
      }
      # Activity metrics
      votesAggregate {
        count
      }
      hansardDebatesAggregate {
        count
      }
    }
  }
`;
