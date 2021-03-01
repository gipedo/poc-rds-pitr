#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from '@aws-cdk/core';
import { PocRdsPitrStack } from '../lib/poc-rds-pitr-stack';

const app = new cdk.App();
new PocRdsPitrStack(app, 'PocRdsPitrStack');
