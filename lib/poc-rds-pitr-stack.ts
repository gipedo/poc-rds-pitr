import * as cdk from "@aws-cdk/core";
import * as ec2 from "@aws-cdk/aws-ec2";
import * as rds from "@aws-cdk/aws-rds";

interface PocRdsPitrStackProps extends cdk.StackProps {
  readonly trustedDbIngress: string;
}

export class PocRdsPitrStack extends cdk.Stack {
  readonly vpc: ec2.Vpc;
  public db: rds.DatabaseInstance;
  public dbSg: ec2.SecurityGroup;
  public dbSecret: rds.DatabaseSecret;

  constructor(scope: cdk.Construct, id: string, props: PocRdsPitrStackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, "RdsVPC", {
      cidr: "10.0.0.0/16",
      maxAzs: 2,
    });

    this.dbSecret = new rds.DatabaseSecret(this, "BackendDbSecret", {
      username: "postgres",
    });

    this.dbSg = new ec2.SecurityGroup(this, "RdsSg", {
      vpc: this.vpc,
      allowAllOutbound: true,
      securityGroupName: "RdsSecurityGroup",
    });
    this.dbSg.connections.allowFrom(
      ec2.Peer.ipv4(props.trustedDbIngress),
      ec2.Port.tcp(5432)
    );

    this.db = new rds.DatabaseInstance(this, "BackendDatabase", {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_12_5,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE3,
        ec2.InstanceSize.SMALL
      ),
      vpc: this.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC }, // IMPORTANT: Dangerous, lab only!
      publiclyAccessible: true, // IMPORTANT: Dangerous, lab only!
      securityGroups: [this.dbSg],
      deletionProtection: false, // IMPORTANT: Dangerous, lab only!
      credentials: rds.Credentials.fromSecret(this.dbSecret),
      allocatedStorage: 10,
      maxAllocatedStorage: 30,
      storageEncrypted: true,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // IMPORTANT: Dangerous, lab only!
      databaseName: cdk.Stack.of(this).stackName,
    });
  }
}
