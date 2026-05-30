FROM ubuntu:22.04
SHELL ["/bin/bash", "-lc"]
RUN <<'__ENDLESS_DOCKER_POST__'
    set -eux

    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        ca-certificates
    python3 -m pip install --no-cache-dir pytest
    apt-get clean
    rm -rf /var/lib/apt/lists/*

    if ! id -u user >/dev/null 2>&1; then
        useradd -m -u 1000 -s /bin/bash user
    fi

    mkdir -p /home/user/operator-work/manifests/raw
    mkdir -p /home/user/operator-work/manifests/normalized
    mkdir -p /home/user/operator-work/reports

    cat > /home/user/operator-work/manifests/raw/bundle.yaml <<'EOF'
# Operator bundle assembled by release tooling
---
apiVersion: v1
kind: Namespace
metadata:
  name: operators
  labels:
    owner: platform
---
# service account for the controller
apiVersion: v1
kind: ServiceAccount
metadata:
  name: sample-operator-controller-manager
  namespace: operators
  labels:
    app.kubernetes.io/name: sample-operator
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-operator-controller-manager
  namespace: operators
  annotations:
    platform.example.com/namespace-scope: "operators"
spec:
  replicas: 1
  selector:
    matchLabels:
      control-plane: controller-manager
  template:
    metadata:
      labels:
        control-plane: controller-manager
        namespace: keep-this-label
    spec:
      serviceAccountName: sample-operator-controller-manager
      containers:
        # this sidecar must not receive manager env changes
        - name: kube-rbac-proxy
          image: quay.io/brancz/kube-rbac-proxy:v0.13.1
          env:
            - name: WATCH_NAMESPACE
              value: proxy-system
          ports:
            - containerPort: 8443
              name: https
        - name: manager
          image: quay.io/example/sample-operator:1.8.0
          imagePullPolicy: IfNotPresent
          env:
            - name: WATCH_NAMESPACE
              value: operators
            - name: LOG_LEVEL
              value: info
            - name: FEATURE_GATES
              value: StableOnly
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: sample-operator-manager-rolebinding
  labels:
    namespace: do-not-change-this-label
subjects:
  - kind: ServiceAccount
    name: sample-operator-controller-manager
    namespace: operators
  - kind: User
    name: ci-bot@example.com
    namespace: external-directory
roleRef:
  kind: ClusterRole
  name: sample-operator-manager-role
  apiGroup: rbac.authorization.k8s.io
---
# Metrics service must remain scoped to operators
apiVersion: v1
kind: Service
metadata:
  name: sample-operator-metrics
  namespace: operators
spec:
  selector:
    control-plane: controller-manager
  ports:
    - name: https
      port: 8443
      targetPort: https
EOF

    chown -R user:user /home/user/operator-work
    chmod -R u+rwX,go+rX /home/user/operator-work

chmod -R a+rwX /home/user
__ENDLESS_DOCKER_POST__
WORKDIR /home/user
