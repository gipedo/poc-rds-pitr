import { expect as expectCDK, matchTemplate, MatchStyle } from '@aws-cdk/assert';
import * as cdk from '@aws-cdk/core';
import * as PocRdsPitr from '../lib/poc-rds-pitr-stack';

test('Empty Stack', () => {
    const app = new cdk.App();
    // WHEN
    const stack = new PocRdsPitr.PocRdsPitrStack(app, 'MyTestStack');
    // THEN
    expectCDK(stack).to(matchTemplate({
      "Resources": {}
    }, MatchStyle.EXACT))
});
